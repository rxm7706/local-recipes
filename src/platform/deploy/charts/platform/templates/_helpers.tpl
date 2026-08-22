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
Image reference from an image dict ({registry, repository, tag}) --
registry-relocatable (CAP-6): the registry prefix is prepended only when
set, so every image in this chart re-points to an internal mirror through
values alone.
*/}}
{{- define "platform.imageRef" -}}
{{- if .registry }}
{{- printf "%s/%s:%s" .registry .repository (.tag | toString) }}
{{- else }}
{{- printf "%s:%s" .repository (.tag | toString) }}
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
The Host header kubelet probes must send: the FIRST entry of
django.allowedHosts. production.py's ALLOWED_HOSTS (env.list) would 400
a bare-IP probe request otherwise.
*/}}
{{- define "platform.probeHost" -}}
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
- name: DJANGO_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.existingSecret | quote }}
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
      name: {{ .Values.existingSecret | quote }}
      key: DATABASE_URL
- name: REDIS_URL
  value: {{ printf "redis://%s-redis:6379/0" (include "platform.fullname" .) | quote }}
{{- end }}
