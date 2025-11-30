# Descargar artículos de PubMed

Ejecuta la descarga de artículos de PubMed con autores españoles.

## Configuración

Antes de ejecutar, editar `config/pubmed_config.yaml`:

```yaml
search:
  query: "Spain[Affiliation]"
  date_from: "2020/01/01"
  date_to: "2024/12/31"
  max_articles: 1000  # null = sin límite
```

## Ejecución

```bash
cd /home/marc/db-projects/pubmed
source venv/bin/activate

# Descarga nueva
python scripts/download_pubmed.py

# Reanudar descarga interrumpida
python scripts/download_pubmed.py --resume
```

## Opciones del script

- `--resume`: Continúa una descarga previa desde donde se quedó
- `--config <archivo>`: Usa un archivo de configuración personalizado
