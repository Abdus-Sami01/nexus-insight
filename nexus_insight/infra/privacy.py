import logging
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

logger = logging.getLogger(__name__)

class PrivacyService:
    """
    Service for redacting PII from text before sending to external LLMs.
    Uses Microsoft Presidio with spaCy.
    """
    
    def __init__(self):
        try:
            from presidio_analyzer.nlp_engine import NlpEngineProvider
            
            # Configure to use small model to save 400MB and improve speed
            configuration = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
            }
            provider = NlpEngineProvider(nlp_configuration=configuration)
            nlp_engine = provider.create_engine()
            
            self.analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
            self.anonymizer = AnonymizerEngine()
            # Define standard operators
            self.operators = {
                "PERSON": OperatorConfig("replace", {"new_value": "<PERSON>"}),
                "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL>"}),
                "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<PHONE>"}),
                "LOCATION": OperatorConfig("replace", {"new_value": "<LOCATION>"}),
            }
        except Exception as e:
            logger.error(f"Failed to initialize Presidio: {e}. Privacy redaction will be disabled.")
            self.analyzer = None
            self.anonymizer = None

    def redact(self, text: str) -> str:
        """Redacts PII from the given text."""
        if not text or not self.analyzer:
            return text
            
        try:
            results = self.analyzer.analyze(text=text, language='en', entities=list(self.operators.keys()))
            anonymized_result = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators=self.operators
            )
            return anonymized_result.text
        except Exception as e:
            logger.warning(f"Redaction failed: {e}")
            return text
