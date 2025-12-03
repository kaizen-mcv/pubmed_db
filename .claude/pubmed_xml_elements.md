# Elementos XML Disponibles en PubMed (DTD 2024)

Referencia completa de los 120+ elementos XML que se pueden extraer de PubMed.

**Fuente oficial:** [PubMed DTD 2024](https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_240101.dtd)

---

## Estructura Principal

| Elemento | Descripción |
|----------|-------------|
| `PubmedArticleSet` | Contenedor raíz de artículos |
| `PubmedArticle` | Un artículo individual |
| `MedlineCitation` | Datos de citación MEDLINE |
| `PubmedData` | Metadatos de PubMed |
| `Article` | Contenedor del artículo |

---

## Identificadores

| Elemento | Descripción |
|----------|-------------|
| `PMID` | PubMed ID único |
| `ArticleId` | IDs adicionales (DOI, PMC, etc.) |
| `ArticleIdList` | Lista de identificadores |
| `ELocationID` | Identificador electrónico (DOI, PII) |
| `AccessionNumber` | Números de acceso (GenBank, etc.) |
| `AccessionNumberList` | Lista de accession numbers |
| `OtherID` | Otros identificadores |

---

## Título y Abstract

| Elemento | Descripción |
|----------|-------------|
| `ArticleTitle` | Título del artículo |
| `VernacularTitle` | Título en idioma original |
| `Abstract` | Contenedor del resumen |
| `AbstractText` | Texto del resumen (puede tener secciones) |
| `OtherAbstract` | Resumen en otro idioma |
| `CopyrightInformation` | Info de copyright |

---

## Autores e Investigadores

| Elemento | Descripción |
|----------|-------------|
| `AuthorList` | Lista de autores |
| `Author` | Autor individual |
| `LastName` | Apellido |
| `ForeName` | Nombre |
| `Initials` | Iniciales |
| `Suffix` | Sufijo (Jr, III, etc.) |
| `CollectiveName` | Nombre de grupo/consorcio |
| `Identifier` | ORCID u otros identificadores |
| `AffiliationInfo` | Contenedor de afiliación |
| `Affiliation` | Texto de afiliación institucional |
| `InvestigatorList` | Lista de investigadores |
| `Investigator` | Investigador individual |

---

## Revista (Journal)

| Elemento | Descripción |
|----------|-------------|
| `Journal` | Contenedor de revista |
| `ISSN` | ISSN de la revista |
| `ISSNLinking` | ISSN de enlace |
| `JournalIssue` | Número de la revista |
| `Volume` | Volumen |
| `Issue` | Número |
| `PubDate` | Fecha de publicación |
| `Title` | Título completo de revista |
| `ISOAbbreviation` | Abreviatura ISO |
| `MedlineJournalInfo` | Info adicional de revista |
| `Country` | País de publicación |
| `MedlineTA` | Abreviatura MEDLINE |
| `NlmUniqueID` | ID único NLM de revista |

---

## Fechas

| Elemento | Descripción |
|----------|-------------|
| `PubDate` | Fecha de publicación |
| `ArticleDate` | Fecha del artículo (electrónico) |
| `DateCompleted` | Fecha de procesamiento completado |
| `DateRevised` | Fecha de última revisión |
| `PubMedPubDate` | Fechas de PubMed (received, accepted, etc.) |
| `Year` | Año |
| `Month` | Mes |
| `Day` | Día |
| `Hour` | Hora |
| `Minute` | Minuto |
| `Second` | Segundo |
| `Season` | Estación (Spring, Fall, etc.) |
| `MedlineDate` | Fecha en formato MEDLINE |

---

## Paginación

| Elemento | Descripción |
|----------|-------------|
| `Pagination` | Contenedor de páginas |
| `MedlinePgn` | Páginas formato MEDLINE (ej: "123-45") |
| `StartPage` | Página inicial |
| `EndPage` | Página final |

---

## Clasificación y Vocabulario Controlado

| Elemento | Descripción |
|----------|-------------|
| `MeshHeadingList` | Lista de términos MeSH |
| `MeshHeading` | Término MeSH individual |
| `DescriptorName` | Descriptor principal |
| `QualifierName` | Calificador (subheading) |
| `KeywordList` | Lista de palabras clave |
| `Keyword` | Palabra clave |
| `SupplMeshList` | MeSH suplementarios |
| `SupplMeshName` | Nombre MeSH suplementario |
| `PublicationTypeList` | Lista de tipos de publicación |
| `PublicationType` | Tipo de publicación |

---

## Sustancias Químicas

| Elemento | Descripción |
|----------|-------------|
| `ChemicalList` | Lista de químicos |
| `Chemical` | Químico individual |
| `NameOfSubstance` | Nombre de la sustancia |
| `RegistryNumber` | Número CAS u otro registro |

---

## Financiación (Grants)

| Elemento | Descripción |
|----------|-------------|
| `GrantList` | Lista de becas/grants |
| `Grant` | Grant individual |
| `GrantID` | ID del grant |
| `Acronym` | Acrónimo de la agencia |
| `Agency` | Agencia financiadora |
| `Country` | País del grant |

---

## Genes

| Elemento | Descripción |
|----------|-------------|
| `GeneSymbolList` | Lista de símbolos de genes |
| `GeneSymbol` | Símbolo de gen |

---

## Bases de Datos Relacionadas

| Elemento | Descripción |
|----------|-------------|
| `DataBankList` | Lista de bancos de datos |
| `DataBank` | Banco de datos |
| `DataBankName` | Nombre (GenBank, ClinicalTrials.gov, etc.) |

---

## Comentarios y Correcciones

| Elemento | Descripción |
|----------|-------------|
| `CommentsCorrectionsList` | Lista de comentarios/correcciones |
| `CommentsCorrections` | Comentario, errata, retractación |
| `RefSource` | Fuente de referencia |
| `Note` | Nota |

---

## Referencias Bibliográficas

| Elemento | Descripción |
|----------|-------------|
| `ReferenceList` | Lista de referencias citadas |
| `Reference` | Referencia individual |
| `Citation` | Texto de citación |
| `ArticleIdList` | IDs de artículos citados |

---

## Otros Campos

| Elemento | Descripción |
|----------|-------------|
| `Language` | Idioma del artículo (eng, spa, etc.) |
| `CoiStatement` | Declaración de conflicto de interés |
| `NumberOfReferences` | Número de referencias |
| `CitationSubset` | Subconjunto de citación |
| `GeneralNote` | Nota general |
| `SpaceFlightMission` | Misión espacial (si aplica) |
| `PersonalNameSubjectList` | Lista de personas como tema |
| `PersonalNameSubject` | Persona como tema del artículo |
| `History` | Historial de estados del artículo |
| `PublicationStatus` | Estado de publicación |
| `ObjectList` | Lista de objetos |
| `Object` | Objeto (estructura 3D, dataset, etc.) |

---

## Libros (BookDocument)

| Elemento | Descripción |
|----------|-------------|
| `Book` | Contenedor de libro |
| `BookTitle` | Título del libro |
| `Publisher` | Editorial |
| `PublisherName` | Nombre de editorial |
| `PublisherLocation` | Ubicación de editorial |
| `Edition` | Edición |
| `Isbn` | ISBN |
| `CollectionTitle` | Título de colección |
| `VolumeTitle` | Título del volumen |
| `Medium` | Medio (Print, Internet) |
| `Section` | Sección |
| `Sections` | Lista de secciones |
| `SectionTitle` | Título de sección |

---

## Formato de Texto (dentro de abstracts/títulos)

| Elemento | Descripción |
|----------|-------------|
| `b` | Negrita |
| `i` | Cursiva |
| `u` | Subrayado |
| `sub` | Subíndice |
| `sup` | Superíndice |
| `DispFormula` | Fórmula matemática |

---

## Comparación: Proyecto Actual vs Disponible

| Categoría | En uso | Disponible |
|-----------|--------|------------|
| Identificadores | 2 (PMID, DOI) | 7+ |
| Artículo | 5 | 10+ |
| Autores | 5 | 12+ |
| Revista | 2 | 10+ |
| Fechas | 1 | 12+ |
| Clasificación | 3 | 10+ |
| Financiación | 0 | 5 |
| Químicos | 0 | 3 |
| Referencias | 0 | 4 |
| **TOTAL** | **~16** | **120+** |

---

## Campos Recomendados para Añadir

Para análisis de investigadores españoles, estos campos serían útiles:

1. **`Language`** - Filtrar por idioma
2. **`GrantList`** - Ver qué financiación reciben
3. **`Volume`, `Issue`, `MedlinePgn`** - Citación completa
4. **`Country`** - País de la revista
5. **`ChemicalList`** - Sustancias estudiadas
6. **`ArticleDate`** - Fecha de publicación electrónica
7. **`CoiStatement`** - Conflictos de interés
8. **`DataBankList`** - Datos en repositorios públicos
