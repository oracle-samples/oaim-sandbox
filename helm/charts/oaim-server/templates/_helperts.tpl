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