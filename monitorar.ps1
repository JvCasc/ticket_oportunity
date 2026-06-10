# Script de execução local do monitoramento de preços de passagens.
# Pensado para ser chamado pelo Agendador de Tarefas do Windows 2x por dia.

$ErrorActionPreference = "Stop"

# Garante que o script rode a partir da pasta do projeto, independente de
# onde o Agendador de Tarefas o invoque.
Set-Location -Path $PSScriptRoot

uv run python main.py *>> monitor.log
