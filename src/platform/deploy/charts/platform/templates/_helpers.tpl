{{/*
Expand the name of the chart.
*/}}
{{- define "platform.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Fully qualified app name (standard helm idiom): the release name, or
release-name-chart-name when the release name doesn't already contain the
chart name. `helm install platform ./charts/platform` therefore renders the
web Service simply as "platform" -- the name the OCP overlay chart's
route.service.name default points at.
*/}}
{{- define "platform.fullname" -}}
{{- if contains .Chart.Name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Component names: fullname + a fixed suffix, truncated to 63 AFTER
suffixing (truncating fullname alone would let a long release name push
the suffixed resource names past the 63-char DNS label limit).
*/}}
{{- define "platform.postgres.fullname" -}}
{{- printf "%s-postgres" (include "platform.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Headless governing Service for the postgres StatefulSet (clusterIP: None)
-- see postgres-service.yaml for the rationale. Same truncation rule.
*/}}
{{- define "platform.postgres.headlessServiceName" -}}
{{- printf "%s-postgres-hl" (include "platform.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "platform.redis.fullname" -}}
{{- printf "%s-redis" (include "platform.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "platform.worker.fullname" -}}
{{- printf "%s-worker" (include "platform.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "platform.migrate.fullname" -}}
{{- printf "%s-migrate" (include "platform.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "platform.dbgpt.fullname" -}}
{{- printf "%s-dbgpt" (include "platform.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "platform.dbgpt.pvcName" -}}
{{- printf "%s-dbgpt-sqlite" (include "platform.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
The data services' own ServiceAccount name -- see serviceaccount.yaml for
why postgres/redis get a second SA. Same truncation rule.
*/}}
{{- define "platform.dataServiceAccountName" -}}
{{- printf "%s-data" (include "platform.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Chart label value.
*/}}
{{- define "platform.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels. Callers add their own app.kubernetes.io/component.
*/}}
{{- define "platform.labels" -}}
helm.sh/chart: {{ include "platform.chart" . }}
app.kubernetes.io/name: {{ include "platform.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels (stable subset -- never include version/chart here).
*/}}
{{- define "platform.selectorLabels" -}}
app.kubernetes.io/name: {{ include "platform.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Image reference from (dict "image" <{registry, repository, tag}> "path"
<values path>) -- registry-relocatable (CAP-6): the registry prefix is
prepended only when set, so every image in this chart re-points to an
internal mirror through values alone. The tag is `required` so a nulled
tag fails the render naming its values path instead of shipping
"repo:<nil>".
*/}}
{{- define "platform.imageRef" -}}
{{- $image := .image }}
{{- $tag := required (printf "%s.tag is required (a null tag would render \"%s:<nil>\")" .path $image.repository) $image.tag | toString }}
{{- if $image.registry }}
{{- printf "%s/%s:%s" $image.registry $image.repository $tag }}
{{- else }}
{{- printf "%s:%s" $image.repository $tag }}
{{- end }}
{{- end }}

{{/*
Pull policy for an image dict: force Always when the effective tag is
"latest" -- a mutable tag with IfNotPresent pins every node to whatever
it pulled first, so rollouts silently serve stale images. Any other tag
uses the values-supplied pullPolicy unchanged.
*/}}
{{- define "platform.imagePullPolicy" -}}
{{- if eq (.tag | toString) "latest" }}
{{- "Always" }}
{{- else }}
{{- .pullPolicy }}
{{- end }}
{{- end }}

{{/*
restricted-v2 POD security context for platform-image pods (web, worker,
migrate). HARDCODED, not values-driven -- the story's AC makes these an
invariant, and a values knob would be an invitation to regress them
silently. Deliberately NO runAsUser/runAsGroup/fsGroup: OCP's
restricted-v2 SCC assigns an arbitrary UID at admission, and the image's
own `USER 1001:0` covers vanilla K8s (Containerfile contract).
*/}}
{{- define "platform.restrictedPodSecurityContext" -}}
runAsNonRoot: true
seccompProfile:
  type: RuntimeDefault
{{- end }}

{{/*
restricted-v2 CONTAINER security context -- same invariant status as the
pod-level block above.
*/}}
{{- define "platform.restrictedContainerSecurityContext" -}}
allowPrivilegeEscalation: false
capabilities:
  drop:
    - ALL
{{- end }}

{{/*
The pre-created Secret's name (AD-12), `required` so a nulled/empty
existingSecret fails the render naming the values path instead of
rendering secretKeyRefs against a Secret named "".
*/}}
{{- define "platform.existingSecretName" -}}
{{- required "existingSecret is required -- the name of the pre-created Secret holding DJANGO_SECRET_KEY/DATABASE_URL/POSTGRES_PASSWORD (AD-12)" .Values.existingSecret }}
{{- end }}

{{/*
Validate django.allowedHosts: it must be a comma-separated STRING (a YAML
list would render as "['a', 'b']" into DJANGO_ALLOWED_HOSTS) whose first
entry is non-empty (it becomes the probes' Host header). `fail` names the
values path; called from both djangoEnv and probeHost so every consumer
hits the same guard.
*/}}
{{- define "platform.validateAllowedHosts" -}}
{{- if not (kindIs "string" .Values.django.allowedHosts) }}
{{- fail (printf "django.allowedHosts must be a comma-separated string, got %s" (kindOf .Values.django.allowedHosts)) }}
{{- end }}
{{- if not (trim (first (splitList "," .Values.django.allowedHosts))) }}
{{- fail "django.allowedHosts: the first comma-separated entry trims to empty -- it must name the Host header the kubelet probes send" }}
{{- end }}
{{- end }}

{{/*
The Host header kubelet probes must send: the FIRST entry of
django.allowedHosts. production.py's ALLOWED_HOSTS (env.list) would 400
a bare-IP probe request otherwise.
*/}}
{{- define "platform.probeHost" -}}
{{- include "platform.validateAllowedHosts" . }}
{{- trim (first (splitList "," .Values.django.allowedHosts)) }}
{{- end }}

{{/*
Shared Django env surface for the web/worker/migrate containers -- mirrors
compose.yml's wiring exactly. Secrets arrive ONLY by secretKeyRef into the
pre-created existingSecret (AD-12); DATABASE_URL is the operator's whole
URL from that Secret, never composed in templates (composing
user:pass@host here would drag the password into the render path).
REDIS_URL is computed: no credential in it, and the redis Service name is
this chart's own.
*/}}
{{- define "platform.djangoEnv" -}}
{{- include "platform.validateAllowedHosts" . -}}
- name: DJANGO_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "platform.existingSecretName" . | quote }}
      key: DJANGO_SECRET_KEY
- name: DJANGO_ADMIN_URL
  value: {{ .Values.django.adminUrl | quote }}
- name: DJANGO_ALLOWED_HOSTS
  value: {{ .Values.django.allowedHosts | quote }}
- name: DJANGO_SECURE_SSL_REDIRECT
  value: {{ .Values.django.secureSslRedirect | quote }}
- name: DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: {{ include "platform.existingSecretName" . | quote }}
      key: DATABASE_URL
- name: REDIS_URL
  value: {{ printf "redis://%s:6379/0" (include "platform.redis.fullname" .) | quote }}
- name: DBGPT_SIDECAR_BASE_URL
  value: {{ printf "http://%s:5670" (include "platform.dbgpt.fullname" .) | quote }}
{{- end }}
