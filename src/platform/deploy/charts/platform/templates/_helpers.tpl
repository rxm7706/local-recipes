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

{{- define "platform.redis.roleFullname" -}}
{{- $base := include "platform.fullname" .root | trunc 50 | trimSuffix "-" }}
{{- printf "%s-redis-%s" $base .role | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "platform.redisBroker.fullname" -}}
{{- include "platform.redis.roleFullname" (dict "root" . "role" "broker") }}
{{- end }}

{{- define "platform.redisCache.fullname" -}}
{{- include "platform.redis.roleFullname" (dict "root" . "role" "cache") }}
{{- end }}

{{- define "platform.redis.fullname" -}}
{{- include "platform.redisBroker.fullname" . }}
{{- end }}

{{- define "platform.media.pvcName" -}}
{{- printf "%s-media" (include "platform.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "platform.worker.fullname" -}}
{{- printf "%s-worker" (include "platform.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{/*
Story 42.4: the builds pool and the beat scheduler. Same truncation rule.
*/}}
{{- define "platform.workerBuilds.fullname" -}}
{{- printf "%s-worker-builds" (include "platform.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "platform.beat.fullname" -}}
{{- printf "%s-beat" (include "platform.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{/*
Story 42.3: per-station event consumer, from (dict "root" $ "station" <token>).
*/}}
{{- define "platform.consumeEvents.fullname" -}}
{{- $base := include "platform.fullname" .root | trunc 40 | trimSuffix "-" }}
{{- printf "%s-consume-events-%s" $base .station | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "platform.migrate.fullname" -}}
{{- printf "%s-migrate" (include "platform.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "platform.liquibase.fullname" -}}
{{- printf "%s-liquibase" (include "platform.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "platform.postgresBackup.fullname" -}}
{{- printf "%s-postgres-backup" (include "platform.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "platform.postgresBackup.pvcName" -}}
{{- printf "%s-postgres-backup" (include "platform.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "platform.dbgpt.fullname" -}}
{{- printf "%s-dbgpt" (include "platform.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "platform.dbgpt.pvcName" -}}
{{- printf "%s-dbgpt-sqlite" (include "platform.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "platform.redisBroker.pvcName" -}}
{{- printf "%s-redis-broker" (include "platform.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Parse a memory quantity (Mi/Gi/mb/gb) to an integer byte count for
template-time comparison. Unrecognized units fail the render naming the
input value (Story 40.2).
*/}}
{{- define "platform.parseMemoryBytes" -}}
{{- $raw := lower (trim (toString .)) -}}
{{- $num := regexFind "^[0-9]+" $raw | atoi -}}
{{- if hasSuffix "gi" $raw -}}
{{- mul $num 1073741824 -}}
{{- else if hasSuffix "mi" $raw -}}
{{- mul $num 1048576 -}}
{{- else if hasSuffix "gb" $raw -}}
{{- mul $num 1000000000 -}}
{{- else if hasSuffix "mb" $raw -}}
{{- mul $num 1000000 -}}
{{- else if hasSuffix "g" $raw -}}
{{- mul $num 1000000000 -}}
{{- else if hasSuffix "m" $raw -}}
{{- mul $num 1000000 -}}
{{- else -}}
{{- fail (printf "platform.parseMemoryBytes: unrecognized memory unit in %q (use Mi/Gi/mb/gb)" .) -}}
{{- end -}}
{{- end }}

{{- define "platform.mcpHost.fullname" -}}
{{- printf "%s-mcp-host" (include "platform.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "platform.keycloak.fullname" -}}
{{- printf "%s-keycloak" (include "platform.fullname" .) | trunc 63 | trimSuffix "-" }}
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
Image reference from (dict "image" <{registry, repository, tag, digest}>
"path" <values path>) -- registry-relocatable (CAP-6): the registry
prefix is prepended only when set. Story 43.4: deploy by digest OR a
pinned non-latest tag; `latest` is refused; bare renders fail naming the
values path instead of shipping a mutable default.
*/}}
{{- define "platform.imageRef" -}}
{{- $image := .image }}
{{- $path := .path }}
{{- $digest := trim (toString (default "" $image.digest)) -}}
{{- if $digest -}}
{{- if $image.registry -}}
{{- printf "%s/%s@%s" $image.registry $image.repository $digest -}}
{{- else -}}
{{- printf "%s@%s" $image.repository $digest -}}
{{- end -}}
{{- else -}}
{{- $tag := trim (toString (default "" $image.tag)) -}}
{{- if not $tag -}}
{{- fail (printf "%s.digest or %s.tag is required (deploy by digest or a pinned tag; no mutable default)" $path $path) -}}
{{- end -}}
{{- if eq $tag "latest" -}}
{{- fail (printf "%s.tag=%q is refused (mutable tags are forbidden; set %s.digest or a pinned tag)" $path $tag $path) -}}
{{- end -}}
{{- if $image.registry -}}
{{- printf "%s/%s:%s" $image.registry $image.repository $tag -}}
{{- else -}}
{{- printf "%s:%s" $image.repository $tag -}}
{{- end -}}
{{- end -}}
{{- end }}

{{/*
Pull policy for an image dict: digests are immutable (use values
pullPolicy). Force Always when the effective tag is "latest" -- defense
in depth even though the render refuses that tag (Story 43.4).
*/}}
{{- define "platform.imagePullPolicy" -}}
{{- $digest := trim (toString (default "" .digest)) -}}
{{- if $digest -}}
{{- .pullPolicy -}}
{{- else if eq (.tag | toString) "latest" -}}
{{- "Always" -}}
{{- else -}}
{{- .pullPolicy -}}
{{- end -}}
{{- end }}

{{/*
restricted-v2 POD security context for platform-image pods (web, worker,
migrate, liquibase). HARDCODED, not values-driven -- the story's AC makes these an
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
{{- required "existingSecret is required -- the name of the pre-created Secret holding DJANGO_SECRET_KEY/DATABASE_URL/MIGRATION_DATABASE_URL/POSTGRES_PASSWORD/REDIS_PASSWORD (AD-12)" .Values.existingSecret }}
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
REDIS_BROKER_URL / REDIS_CACHE_URL are computed from the two Redis
Service names plus REDIS_PASSWORD (secretKeyRef, expanded via
$(REDIS_PASSWORD) at runtime -- the password never enters the render
path). REDIS_URL stays an alias of the broker for leftover consumers.
Story 12.6 AUTH + Story 20.2 cache≠broker.
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
- name: REDIS_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "platform.existingSecretName" . | quote }}
      key: {{ required "redis.passwordSecretKey is required" .Values.redis.passwordSecretKey | quote }}
{{- /* CAP-18 host assertion signing keypair -- optional: true so a pod
       without them still boots; mint_assertion()/verify_assertion() raise
       AssertionRefusedError until they're present (found running the CAP-3
       attended CRC exercise, 2026-09-12: values.yaml's existingSecret
       comment above has the full story). */}}
- name: PYFORGE_ASSERTION_PRIVATE_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "platform.existingSecretName" . | quote }}
      key: PYFORGE_ASSERTION_PRIVATE_KEY
      optional: true
- name: PYFORGE_ASSERTION_PUBLIC_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "platform.existingSecretName" . | quote }}
      key: PYFORGE_ASSERTION_PUBLIC_KEY
      optional: true
{{- /* Story 50.3 / pap:AD-1's 2026-09-10 dated exception: object storage is
       CONSUMED only, never self-hosted -- these three point at whatever
       S3-compatible endpoint ops provisioned (production target: NetApp
       StorageGRID), never a server this chart deploys itself. optional:
       true for the same reason as the assertion keypair above: no feature
       calls config.object_storage.object_storage_client() yet (that
       module's own docstring calls this "future, story-by-story work"), so
       a pod without them must still boot -- ImproperlyConfigured only
       fires if/when something actually calls that function. */}}
- name: OBJECT_STORAGE_ENDPOINT_URL
  valueFrom:
    secretKeyRef:
      name: {{ include "platform.existingSecretName" . | quote }}
      key: OBJECT_STORAGE_ENDPOINT_URL
      optional: true
- name: OBJECT_STORAGE_ACCESS_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "platform.existingSecretName" . | quote }}
      key: OBJECT_STORAGE_ACCESS_KEY
      optional: true
- name: OBJECT_STORAGE_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "platform.existingSecretName" . | quote }}
      key: OBJECT_STORAGE_SECRET_KEY
      optional: true
{{- if .Values.redis.external.enabled }}
- name: REDIS_BROKER_URL
  value: {{ required "redis.external.brokerUrl is required when redis.external.enabled is true" .Values.redis.external.brokerUrl | quote }}
- name: REDIS_CACHE_URL
  value: {{ required "redis.external.cacheUrl is required when redis.external.enabled is true" .Values.redis.external.cacheUrl | quote }}
- name: REDIS_URL
  value: {{ (.Values.redis.external.url | default .Values.redis.external.brokerUrl) | quote }}
{{- else }}
- name: REDIS_BROKER_URL
  value: {{ printf "redis://:$(REDIS_PASSWORD)@%s:6379/0" (include "platform.redisBroker.fullname" .) | quote }}
- name: REDIS_CACHE_URL
  value: {{ printf "redis://:$(REDIS_PASSWORD)@%s:6379/0" (include "platform.redisCache.fullname" .) | quote }}
- name: REDIS_URL
  value: {{ printf "redis://:$(REDIS_PASSWORD)@%s:6379/0" (include "platform.redisBroker.fullname" .) | quote }}
{{- end }}
- name: MEDIA_ROOT
  value: {{ .Values.media.mountPath | quote }}
{{- if .Values.sidecar.enabled }}
- name: DBGPT_SIDECAR_BASE_URL
  value: {{ printf "http://%s:5670" (include "platform.dbgpt.fullname" .) | quote }}
{{- end }}
- name: MCP_HOST_SIDECAR_BASE_URL
  value: {{ printf "http://%s:8090" (include "platform.mcpHost.fullname" .) | quote }}
- name: PYFORGE_FLAGS_PATH
  value: {{ printf "%s/%s" .Values.flags.mountPath .Values.flags.fileName | quote }}
- name: FLAGD_RESOLVER
  value: "file"
- name: FLAGD_OFFLINE_FLAG_SOURCE_PATH
  value: {{ printf "%s/%s" .Values.flags.mountPath .Values.flags.fileName | quote }}
{{- /* Story 42.4: the builds pool's hard limit, on EVERY platform pod, so the
       supervisor's worker-lost sweep (wherever it runs) and the broker
       visibility timeout agree with the --time-limit the builds pod passes. */}}
- name: CELERY_BUILDS_TASK_TIME_LIMIT
  value: {{ int .Values.worker.builds.taskTimeLimitSeconds | quote }}
{{- include "platform.oidcEnv" . }}
{{- end }}

{{/*
Story 48.9 / CAP-1: OIDC env wired for every platform-image pod. Bundled
profile computes issuer/JWKS from in-cluster Keycloak; BYO reads values.
*/}}
{{- define "platform.oidcEnv" -}}
{{- if eq .Values.oidc.profile "bundled" }}
{{- $issuerHost := required "keycloak.ingress.host is required when oidc.profile=bundled" .Values.keycloak.ingress.host }}
{{- $issuer := printf "https://%s/realms/%s" $issuerHost .Values.keycloak.realm }}
{{/*
The full in-cluster Service FQDN (not the bare short name) so
django_pyforge's JWKS verifier can recognize this as a same-cluster
Service DNS name and allow the scheme to stay http:// -- Kubernetes'
own CoreDNS is the sole authority for the .svc.cluster.local zone, so
this is not a spoofable trust signal (see jwks.py's own comment).
*/}}
{{- $jwks := printf "http://%s.%s.svc.cluster.local:8080/realms/%s/protocol/openid-connect/certs" (include "platform.keycloak.fullname" .) .Release.Namespace .Values.keycloak.realm }}
- name: COMPONENT_IDENTITY_CLAIM
  value: {{ .Values.oidc.identityClaim | quote }}
- name: COMPONENT_GROUP_CLAIM
  value: {{ .Values.oidc.groupClaim | quote }}
- name: COMPONENT_STAFF_GROUP
  value: {{ .Values.oidc.staffGroup | quote }}
- name: COMPONENT_SUPERUSER_GROUP
  value: {{ .Values.oidc.superuserGroup | quote }}
- name: COMPONENT_OIDC_ISSUER
  value: {{ $issuer | quote }}
- name: COMPONENT_OIDC_CLIENT_ID
  value: {{ .Values.keycloak.clientId | quote }}
- name: COMPONENT_OIDC_JWKS_URL
  value: {{ $jwks | quote }}
- name: COMPONENT_OIDC_AUDIENCE
  value: {{ .Values.keycloak.clientId | quote }}
- name: COMPONENT_OIDC_PROVIDER_NAME
  value: {{ .Values.oidc.providerName | quote }}
{{- if not .Values.keycloak.publicClient }}
- name: COMPONENT_OIDC_CLIENT_SECRET
  valueFrom:
    secretKeyRef:
      name: {{ include "platform.existingSecretName" . | quote }}
      key: COMPONENT_OIDC_CLIENT_SECRET
{{- end }}
{{- else if eq .Values.oidc.profile "byo" }}
{{- $issuer := required "oidc.byo.issuer is required when oidc.profile=byo" .Values.oidc.byo.issuer }}
{{- $jwks := required "oidc.byo.jwksUrl is required when oidc.profile=byo" .Values.oidc.byo.jwksUrl }}
{{- $clientId := required "oidc.byo.clientId is required when oidc.profile=byo" .Values.oidc.byo.clientId }}
{{- $audience := .Values.oidc.byo.audience | default $clientId }}
- name: COMPONENT_IDENTITY_CLAIM
  value: {{ .Values.oidc.identityClaim | quote }}
- name: COMPONENT_GROUP_CLAIM
  value: {{ .Values.oidc.groupClaim | quote }}
- name: COMPONENT_STAFF_GROUP
  value: {{ .Values.oidc.staffGroup | quote }}
- name: COMPONENT_SUPERUSER_GROUP
  value: {{ .Values.oidc.superuserGroup | quote }}
- name: COMPONENT_OIDC_ISSUER
  value: {{ $issuer | quote }}
- name: COMPONENT_OIDC_CLIENT_ID
  value: {{ $clientId | quote }}
- name: COMPONENT_OIDC_JWKS_URL
  value: {{ $jwks | quote }}
- name: COMPONENT_OIDC_AUDIENCE
  value: {{ $audience | quote }}
- name: COMPONENT_OIDC_PROVIDER_NAME
  value: {{ .Values.oidc.providerName | quote }}
- name: COMPONENT_OIDC_CLIENT_SECRET
  valueFrom:
    secretKeyRef:
      name: {{ include "platform.existingSecretName" . | quote }}
      key: {{ required "oidc.byo.clientSecretKey is required when oidc.profile=byo" .Values.oidc.byo.clientSecretKey | quote }}
{{- else }}
{{- fail (printf "oidc.profile must be bundled or byo, got %q" .Values.oidc.profile) }}
{{- end }}
{{- end }}

{{/*
Liquibase Job env (canopy AD-9 / FR-21a): migration-role URL only.
Never DATABASE_URL (app role is DML-only). Host in that URL must be the
in-cluster postgres Service, not a pooling proxy -- enforced in
db/liquibase_update.py, not by composing the URL here (AD-12).
*/}}
{{- define "platform.liquibaseEnv" -}}
- name: MIGRATION_DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: {{ include "platform.existingSecretName" . | quote }}
      key: MIGRATION_DATABASE_URL
{{- end }}

{{/*
spec-mcp-host-real-station-tools CAP-1: a station's real in-process MCP app
(currently marshal only) needs django_pyforge's ORM against the SAME
Postgres the web pod uses -- the app-role DML URL (never MIGRATION_DATABASE_URL;
this sidecar only reads/writes RunState/McpHandle rows, it never migrates).
DJANGO_SECRET_KEY is required by Django itself even though this sidecar
serves no Django views; PYFORGE_ASSERTION_PUBLIC_KEY is optional (absent
means every publish call is refused, matching the web pod's own posture).
*/}}
{{- define "platform.mcpHostEnv" -}}
- name: DJANGO_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "platform.existingSecretName" . | quote }}
      key: DJANGO_SECRET_KEY
- name: DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: {{ include "platform.existingSecretName" . | quote }}
      key: DATABASE_URL
- name: PYFORGE_ASSERTION_PUBLIC_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "platform.existingSecretName" . | quote }}
      key: PYFORGE_ASSERTION_PUBLIC_KEY
      optional: true
{{- end }}

{{/*
Story 26.4: directory mount (not subPath) so ConfigMap updates are visible
to the FILE provider poll without a new process.
*/}}
{{- define "platform.flagsVolumeMount" -}}
- name: flags
  mountPath: {{ .Values.flags.mountPath | quote }}
  readOnly: true
{{- end }}

{{- define "platform.flagsVolume" -}}
- name: flags
  configMap:
    name: {{ include "platform.fullname" . }}-flags
{{- end }}

{{/*
Story 48.3 / R-19: reusable NetworkPolicy egress fragments. Peers are
release-scoped podSelectors in the release namespace -- never ipBlock for
in-cluster Services.
*/}}
{{- define "platform.networkPolicy.dnsEgress" -}}
- to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: {{ .Values.networkPolicy.dns.namespace | quote }}
      podSelector:
        matchLabels:
          {{ .Values.networkPolicy.dns.podLabelKey }}: {{ .Values.networkPolicy.dns.podLabelValue | quote }}
  ports:
    - protocol: UDP
      port: {{ .Values.networkPolicy.dns.port }}
    - protocol: TCP
      port: {{ .Values.networkPolicy.dns.port }}
{{- end }}

{{- define "platform.networkPolicy.egressToPostgres" -}}
- to:
    - podSelector:
        matchLabels:
          {{- include "platform.selectorLabels" . | nindent 10 }}
          app.kubernetes.io/component: postgres
  ports:
    - protocol: TCP
      port: 5432
{{- end }}

{{- define "platform.networkPolicy.egressToRedis" -}}
{{- range $role := tuple "cache" "broker" }}
- to:
    - podSelector:
        matchLabels:
          {{- include "platform.selectorLabels" $ | nindent 10 }}
          app.kubernetes.io/component: redis-{{ $role }}
  ports:
    - protocol: TCP
      port: 6379
{{- end }}
{{- end }}

{{- define "platform.networkPolicy.egressToMcpHost" -}}
- to:
    - podSelector:
        matchLabels:
          {{- include "platform.selectorLabels" . | nindent 10 }}
          app.kubernetes.io/component: mcp-host
  ports:
    - protocol: TCP
      port: 8090
{{- end }}

{{- define "platform.networkPolicy.egressToDbgpt" -}}
- to:
    - podSelector:
        matchLabels:
          {{- include "platform.selectorLabels" . | nindent 10 }}
          app.kubernetes.io/component: dbgpt
  ports:
    - protocol: TCP
      port: 5670
{{- end }}

{{- define "platform.networkPolicy.egressToKeycloak" -}}
- to:
    - podSelector:
        matchLabels:
          {{- include "platform.selectorLabels" . | nindent 10 }}
          app.kubernetes.io/component: keycloak
  ports:
    - protocol: TCP
      port: 8080
{{- end }}

{{- define "platform.networkPolicy.platformDataPlaneEgress" -}}
{{ include "platform.networkPolicy.egressToPostgres" . }}
{{ include "platform.networkPolicy.egressToRedis" . }}
{{- end }}

{{- define "platform.networkPolicy.webEgressRules" -}}
{{ include "platform.networkPolicy.platformDataPlaneEgress" . }}
{{ include "platform.networkPolicy.egressToMcpHost" . }}
{{ include "platform.networkPolicy.egressToDbgpt" . }}
{{- if eq .Values.oidc.profile "bundled" }}
{{ include "platform.networkPolicy.egressToKeycloak" . }}
{{- end }}
{{ include "platform.networkPolicy.dnsEgress" . }}
{{- end }}

{{- define "platform.networkPolicy.workerEgressRules" -}}
{{ include "platform.networkPolicy.platformDataPlaneEgress" . }}
{{ include "platform.networkPolicy.egressToDbgpt" . }}
{{- if eq .Values.oidc.profile "bundled" }}
{{ include "platform.networkPolicy.egressToKeycloak" . }}
{{- end }}
{{ include "platform.networkPolicy.dnsEgress" . }}
{{- end }}
