# Oracle AI Microservices Sandbox - Documentation

## Description

This directory contains the documentation for the the [**Oracle AI Microservices Sandbox**](https://github.com/oracle-samples/oaim-sandbox).

## Getting Started - Documentation

The **Oracle AI Microservices Sandbox** documentation is powered by [Hugo](https://gohugo.io/) using the [GeekDocs](https://geekdocs.de/) theme.

To contribute to the documentation, install [Hugo](https://gohugo.io/installation/). Installation instructions vary per Operating System.

From the `docs` directory:

1. Download the [GeekDocs](https://geekdocs.de/) theme
   ```bash
   mkdir -p themes/hugo-geekdoc/
   curl -L https://github.com/thegeeklab/hugo-geekdoc/releases/latest/download/hugo-geekdoc.tar.gz | tar -xz -C themes/hugo-geekdoc/ --strip-components=1
   ```
1. Start Hugo: `hugo serve`

This will serve the documentation on `http://localhost:1313/oaim-sandbox/` for review.
