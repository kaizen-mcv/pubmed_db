-- Tabla de términos MeSH (Medical Subject Headings)
-- Fuente: NLM - https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/asciimesh/
-- Actualización: Anual (enero)

-- Eliminar tabla existente
DROP TABLE IF EXISTS mesh_terms CASCADE;

-- Crear tabla mesh_terms
CREATE TABLE mesh_terms (
    id SERIAL PRIMARY KEY,
    mesh_ui VARCHAR(20) UNIQUE NOT NULL,      -- Unique Identifier (ej: D002318)
    mesh_name VARCHAR(500) NOT NULL,          -- Nombre principal (ej: "Cardiovascular Diseases")
    tree_numbers TEXT,                        -- Códigos jerárquicos separados por ; (ej: "C14;C14.280")
    parent_category CHAR(1),                  -- Categoría raíz: A,B,C,D,E,F,G,H,I,J,K,L,M,N,V,Z
    year_introduced INTEGER,                  -- Año de introducción del término
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para búsquedas eficientes
CREATE INDEX idx_mesh_ui ON mesh_terms(mesh_ui);
CREATE INDEX idx_mesh_name ON mesh_terms(mesh_name);
CREATE INDEX idx_mesh_category ON mesh_terms(parent_category);

-- Comentarios de documentación
COMMENT ON TABLE mesh_terms IS 'Términos MeSH (Medical Subject Headings) de la NLM';
COMMENT ON COLUMN mesh_terms.mesh_ui IS 'Identificador único MeSH (ej: D002318)';
COMMENT ON COLUMN mesh_terms.mesh_name IS 'Nombre principal del término MeSH';
COMMENT ON COLUMN mesh_terms.tree_numbers IS 'Códigos jerárquicos separados por ; (ej: C14;C14.280.647)';
COMMENT ON COLUMN mesh_terms.parent_category IS 'Categoría raíz: C=Diseases, F=Psychiatry, etc.';
COMMENT ON COLUMN mesh_terms.year_introduced IS 'Año en que se introdujo el término en MeSH';
