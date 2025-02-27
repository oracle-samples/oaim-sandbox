{{/* 
Copyright (c) 2024-2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl. 
*/}}

{{/*
Set default value for mtlsWallet if not defined
*/}}
{{- define "getMtlsWallet" -}}
{{- if .Values.adb.mtlsWallet -}}
  {{- .Values.adb.mtlsWallet -}}
{{- else -}}
  {{- dict -}}  # Return an empty dictionary if mtlsWallet is not defined
{{- end -}}
{{- end -}}

{{/*
Set default value for tnsAdmin if not defined
*/}}
{{- define "getTnsAdmin" -}}
{{- if .Values.adb.tnsAdmin -}}
  {{- .Values.adb.tnsAdmin -}}
{{- else -}}
  {{- dict -}}  # Return an empty dictionary if tnsAdmin is not defined
{{- end -}}
{{- end -}}