{{/* 
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl. 
*/}}

{{/*
Expand the name of the chart.
*/}}
{{- define "oaim-sandbox.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "oaim-sandbox.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "oaim-sandbox.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "oaim-sandbox.labels" -}}
helm.sh/chart: {{ include "oaim-sandbox.chart" . }}
{{ include "oaim-sandbox.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "oaim-sandbox.selectorLabels" -}}
app.kubernetes.io/name: {{ include "oaim-sandbox.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "oaim-sandbox.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "oaim-sandbox.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Set the path based on baseUrlPath
*/}}
{{- define "getPath" -}}
{{- $baseUrlPath := .Values.baseUrlPath | default "" -}}
{{- if eq $baseUrlPath "" -}}
/
{{- else if not (hasPrefix "/" $baseUrlPath) -}}
{{- printf "/%s" $baseUrlPath -}}
{{- else -}}
{{- $baseUrlPath -}}
{{- end -}}
{{- end -}}