# Test de Descarga

Ejecuta una descarga de prueba con pocos artículos para verificar que todo funciona.

## Configuración previa

Editar `config/pubmed_config.yaml` para el test:

```yaml
search:
  query: "Spain[Affiliation]"
  date_from: "2020/01/01"
  date_to: "2020/12/31"
  max_articles: 10  # Pocos artículos para prueba
```

## Ejecución

```bash
cd $PROJECT_DIR
source venv/bin/activate

# Primero verificar la conexión a la BD
PGPASSWORD="$PGPASSWORD" psql -h localhost -U pubmed_user -d pubmed_db -c "SELECT COUNT(*) as articulos_antes FROM articles;"

# Ejecutar descarga de prueba
python scripts/download_pubmed.py

# Verificar resultados
PGPASSWORD="$PGPASSWORD" psql -h localhost -U pubmed_user -d pubmed_db << 'EOF'
SELECT COUNT(*) as articulos_despues FROM articles;
SELECT COUNT(*) as autores_espanoles FROM article_authors;

-- Muestra los últimos artículos descargados
SELECT pubmed_id, LEFT(article_title, 60) as titulo, journal_name, publication_types
FROM articles
ORDER BY created_at DESC
LIMIT 5;
EOF
```

## Verificar

1. Cuántos artículos había antes
2. Cuántos hay después
3. Cuántos autores españoles se encontraron
4. Muestra de los últimos artículos
