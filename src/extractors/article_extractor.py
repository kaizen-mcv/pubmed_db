"""
Article field extractor.

Extracts: pubmed_id, article_title, article_abstract, journal_name, journal_issn,
          article_doi, publication_date, publication_types, mesh_terms, author_keywords
"""

from datetime import date
from typing import Any, Dict, Optional


class ArticleExtractor:
    """
    Extracts the main fields of a PubMed XML article.
    """

    # Month name to number mapping
    MONTH_MAP = {
        'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
        'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
        'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12',
        'January': '01', 'February': '02', 'March': '03',
        'April': '04', 'June': '06', 'July': '07',
        'August': '08', 'September': '09', 'October': '10',
        'November': '11', 'December': '12'
    }

    @staticmethod
    def extract_pubmed_id(article_data: Dict[str, Any]) -> int:
        """
        Extract the PubMed ID of the article.

        Args:
            article_data: Dictionary with Entrez article data

        Returns:
            PubMed ID as integer
        """
        return int(article_data['MedlineCitation']['PMID'])

    @staticmethod
    def extract_pubmed_central_id(article_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract the PubMed Central ID (PMC) if it exists.

        Args:
            article_data: Dictionary with article data

        Returns:
            PMC ID (e.g. "PMC1234567") or None
        """
        article_ids = article_data.get('PubmedData', {}).get('ArticleIdList', [])

        for art_id in article_ids:
            if hasattr(art_id, 'attributes'):
                if art_id.attributes.get('IdType') == 'pmc':
                    return str(art_id)

        return None

    @staticmethod
    def extract_article_title(article_data: Dict[str, Any]) -> str:
        """
        Extract the title of the article.

        Args:
            article_data: Dictionary with article data

        Returns:
            Article title
        """
        article = article_data['MedlineCitation']['Article']
        return article.get('ArticleTitle', '')

    @staticmethod
    def extract_article_abstract(article_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract the abstract of the article.

        Handles both structured (with sections) and plain abstracts.

        Args:
            article_data: Dictionary with article data

        Returns:
            Abstract as text or None
        """
        article = article_data['MedlineCitation']['Article']
        abstract_data = article.get('Abstract', {})

        if not abstract_data:
            return None

        abstract_texts = abstract_data.get('AbstractText', [])

        if not abstract_texts:
            return None

        # If it is a list (structured abstract), concatenate
        if isinstance(abstract_texts, list):
            parts = []
            for part in abstract_texts:
                if hasattr(part, 'attributes') and 'Label' in part.attributes:
                    label = part.attributes['Label']
                    parts.append(f"{label}: {str(part)}")
                else:
                    parts.append(str(part))
            return ' '.join(parts)

        return str(abstract_texts)

    @staticmethod
    def extract_article_doi(article_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract the DOI of the article.

        Args:
            article_data: Dictionary with article data

        Returns:
            DOI (e.g. "10.1000/xyz123") or None
        """
        article_ids = article_data.get('PubmedData', {}).get('ArticleIdList', [])

        for art_id in article_ids:
            if hasattr(art_id, 'attributes'):
                if art_id.attributes.get('IdType') == 'doi':
                    return str(art_id)

        return None

    @classmethod
    def extract_publication_date(cls, article_data: Dict[str, Any]) -> Optional[date]:
        """
        Extract the publication date.

        Args:
            article_data: Dictionary with article data

        Returns:
            Date as date object or None
        """
        article = article_data['MedlineCitation']['Article']
        journal = article.get('Journal', {})
        pub_date = journal.get('JournalIssue', {}).get('PubDate', {})

        year = pub_date.get('Year', '')
        month = pub_date.get('Month', '01')
        day = pub_date.get('Day', '01')

        if not year:
            return None

        # Convert month from text to number
        if month in cls.MONTH_MAP:
            month = cls.MONTH_MAP[month]

        try:
            # Ensure correct format
            month = str(month).zfill(2)
            day = str(day).zfill(2)
            return date(int(year), int(month), int(day))
        except (ValueError, TypeError):
            # If it fails, try with year only
            try:
                return date(int(year), 1, 1)
            except (ValueError, TypeError):
                return None

    @staticmethod
    def extract_journal_name(article_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract the journal name.

        Args:
            article_data: Dictionary with article data

        Returns:
            Journal name or None
        """
        article = article_data['MedlineCitation']['Article']
        journal = article.get('Journal', {})
        return journal.get('Title', None)

    @staticmethod
    def extract_journal_issn(article_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract the ISSN of the journal.

        Args:
            article_data: Dictionary with article data

        Returns:
            ISSN (e.g. "1234-5678") or None
        """
        article = article_data['MedlineCitation']['Article']
        journal = article.get('Journal', {})
        issn = journal.get('ISSN', None)

        if issn:
            return str(issn)

        return None

    @staticmethod
    def extract_publication_types(article_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract the publication types of the article.

        Args:
            article_data: Dictionary with article data

        Returns:
            Publication types separated by ; (e.g. "Journal Article; Review") or None
        """
        article = article_data['MedlineCitation']['Article']
        pub_types = article.get('PublicationTypeList', [])

        if not pub_types:
            return None

        types_list = []

        if isinstance(pub_types, list):
            for pub_type in pub_types:
                types_list.append(str(pub_type))
        else:
            types_list.append(str(pub_types))

        return '; '.join(types_list) if types_list else None

    @staticmethod
    def extract_mesh_terms(article_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract the MeSH terms of the article.

        Args:
            article_data: Dictionary with article data

        Returns:
            MeSH terms separated by commas or None
        """
        mesh_list = article_data['MedlineCitation'].get('MeshHeadingList', [])

        if not mesh_list:
            return None

        mesh_terms = []
        for mesh in mesh_list:
            descriptor = mesh.get('DescriptorName', '')
            if descriptor:
                mesh_terms.append(str(descriptor))

        return ', '.join(mesh_terms) if mesh_terms else None

    @staticmethod
    def extract_author_keywords(article_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract the author keywords.

        Args:
            article_data: Dictionary with article data

        Returns:
            Keywords separated by commas or None
        """
        keyword_list = article_data['MedlineCitation'].get('KeywordList', [])

        if not keyword_list:
            return None

        keywords = []
        for kw_group in keyword_list:
            for kw in kw_group:
                keywords.append(str(kw))

        return ', '.join(keywords) if keywords else None
