"""Tool for analyzing documentation quality metrics."""
from typing import Dict, List, Optional
from datetime import datetime
from core.services.logging import setup_logger
from core.services.cache import cache_manager
from ..schemas.quality_metrics import (
    ContentMetrics,
    StructureMetrics,
    CodeMetrics,
    DocumentMetrics,
    QualityAssessment
)

logger = setup_logger(__name__)

class QualityAnalyzer:
    """Analyzes and tracks documentation quality metrics."""

    def __init__(self):
        """Initialize the quality analyzer."""
        self.cache = cache_manager
        self.quality_thresholds = {
            'readability': 0.8,
            'technical_accuracy': 0.9,
            'completeness': 0.85,
            'example_quality': 0.85
        }

    async def analyze_documentation(
        self,
        documentation: Dict[str, str],
        repository_type: str
    ) -> QualityAssessment:
        """
        Analyze documentation quality.
        
        Args:
            documentation: Documentation content by file
            repository_type: Type of repository
            
        Returns:
            QualityAssessment with metrics
        """
        try:
            documents = {}
            
            for file_path, content in documentation.items():
                # Analyze individual document
                doc_metrics = await self._analyze_document(content, repository_type)
                documents[file_path] = doc_metrics

            # Calculate overall quality score
            overall_score = sum(doc.document_score for doc in documents.values()) / len(documents)

            return QualityAssessment(
                repository_type=repository_type,
                documents=documents,
                overall_score=overall_score,
                meets_standards=overall_score >= 0.85,
                required_revisions=await self._get_required_revisions(documents),
                assessment_timestamp=datetime.now()
            )

        except Exception as e:
            logger.error(f"Error analyzing documentation: {str(e)}")
            raise

    async def _analyze_document(self, content: str, repository_type: str) -> DocumentMetrics:
        """Analyze a single documentation file."""
        try:
            # Calculate content metrics
            content_metrics = await self._analyze_content(content)
            
            # Calculate structure metrics
            structure_metrics = await self._analyze_structure(content)
            
            # Calculate code metrics if code blocks present
            code_metrics = await self._analyze_code(content) if '```' in content else None
            
            # Calculate overall document score
            scores = [
                content_metrics.readability_score,
                content_metrics.technical_accuracy,
                content_metrics.completeness,
                structure_metrics.organization
            ]
            if code_metrics:
                scores.append(code_metrics.syntax_correctness)
                
            document_score = sum(scores) / len(scores)
            
            return DocumentMetrics(
                file_path="",  # Will be set by caller
                overall_content=content_metrics,
                overall_structure=structure_metrics,
                overall_code=code_metrics,
                document_score=document_score,
                sections={},  # Detailed section analysis not needed for initial assessment
                critical_issues=[],  # Will be populated if score below threshold
                recommendations=[]  # Will be populated if score below threshold
            )

        except Exception as e:
            logger.error(f"Error analyzing document: {str(e)}")
            raise

    async def _analyze_content(self, content: str) -> ContentMetrics:
        """Analyze content quality metrics."""
        try:
            # Calculate readability (simplified)
            words = content.split()
            sentences = content.split('.')
            avg_words_per_sentence = len(words) / max(len(sentences), 1)
            readability_score = min(1.0, 1.0 - (avg_words_per_sentence - 15) / 25)
            
            # Calculate technical accuracy (baseline)
            technical_accuracy = 0.9  # Baseline, will be refined by TechnicalValidator
            
            # Calculate completeness
            required_sections = {'Overview', 'Installation', 'Usage', 'Configuration'}
            found_sections = {section.strip('#').strip().lower() 
                            for section in content.split('\n') 
                            if section.startswith('#')}
            completeness = len(found_sections.intersection(required_sections)) / len(required_sections)
            
            # Calculate consistency
            consistency = 1.0  # Baseline, should be calculated based on style consistency
            
            # Calculate example quality
            example_blocks = content.count('```')
            example_quality = min(1.0, example_blocks / 5)  # Expect at least 5 examples
            
            return ContentMetrics(
                readability_score=readability_score,
                technical_accuracy=technical_accuracy,
                completeness=completeness,
                consistency=consistency,
                example_quality=example_quality
            )

        except Exception as e:
            logger.error(f"Error analyzing content: {str(e)}")
            raise

    async def _analyze_structure(self, content: str) -> StructureMetrics:
        """Analyze documentation structure."""
        try:
            # Analyze header hierarchy
            headers = [line for line in content.split('\n') if line.startswith('#')]
            header_levels = [len(h.split()[0]) for h in headers]
            
            # Check organization (proper header nesting)
            valid_nesting = all(b - a <= 1 for a, b in zip(header_levels, header_levels[1:]))
            organization = 1.0 if valid_nesting else 0.7
            
            # Check formatting consistency
            formatting = 1.0  # Baseline, should check markdown formatting consistency
            
            # Check hierarchy clarity
            hierarchy = 1.0 if len(set(header_levels)) > 1 else 0.8
            
            # Check internal/external linking
            links = content.count('](')
            linking = min(1.0, links / 5)  # Expect at least 5 links
            
            return StructureMetrics(
                organization=organization,
                formatting=formatting,
                hierarchy=hierarchy,
                linking=linking
            )

        except Exception as e:
            logger.error(f"Error analyzing structure: {str(e)}")
            raise

    async def _analyze_code(self, content: str) -> CodeMetrics:
        """Analyze code examples in documentation."""
        try:
            # Extract code blocks
            code_blocks = content.split('```')[1::2]  # Get odd-indexed elements (inside ```)
            
            if not code_blocks:
                return None
                
            # Calculate metrics
            return CodeMetrics(
                syntax_correctness=1.0,  # Baseline, should be validated by TechnicalValidator
                style_consistency=1.0,  # Baseline, should check code style consistency
                example_completeness=min(1.0, len(code_blocks) / 3),  # Expect at least 3 examples
                documentation_match=1.0  # Baseline, should be validated by TechnicalValidator
            )

        except Exception as e:
            logger.error(f"Error analyzing code: {str(e)}")
            raise

    async def _get_required_revisions(self, documents: Dict[str, DocumentMetrics]) -> List[str]:
        """Determine required revisions based on metrics."""
        revisions = []
        
        for file_path, metrics in documents.items():
            if metrics.document_score < 0.85:
                revisions.append(f"Improve overall quality of {file_path}")
            if metrics.overall_content.readability_score < self.quality_thresholds['readability']:
                revisions.append(f"Improve readability in {file_path}")
            if metrics.overall_content.completeness < self.quality_thresholds['completeness']:
                revisions.append(f"Add missing sections in {file_path}")
                
        return revisions