"""Evidence-preserving baseline. External contextual/embedding providers are not enabled."""
import hashlib
import json
import re
from typing import Protocol

from .models import Extraction, ScreeningRun


class CVParserProvider(Protocol):
    def extract(self, data: bytes, extension: str) -> list[dict]: ...


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class CandidateMatchingProvider(Protocol):
    def evaluate(self, criteria: list[dict], sections: list[dict]) -> dict: ...


ALIASES = {'postgresql': ['postgres', 'postgresql'], 'javascript': ['javascript', 'ecmascript'],
           'aws': ['aws', 'amazon web services'], 'kubernetes': ['kubernetes', 'k8s'],
           'python': ['python'], 'excel': ['excel', 'microsoft excel'], 'c#': ['c#', 'c sharp']}
INJECTION = re.compile(r'ignore (all |the |any |previous )*(instructions|rules)|system prompt|give (me|this candidate) (100|a perfect)|override.*score', re.I)


def evaluate(criteria, sections):
    """Matching terms are evidence of a mention, never proof of proficiency/eligibility."""
    evidence = []
    warnings = ['Local evidence baseline: no semantic model or contextual AI has been run. Mentions are unverified and do not establish competence.']
    suspicious = any(INJECTION.search(section['text']) for section in sections)
    if suspicious:
        warnings.append('Instruction-like document content detected. Automatic scoring withheld; human review required.')
    total = sum(item['weight'] for item in criteria)
    matched = 0
    for criterion in criteria:
        terms = ALIASES.get(criterion['label'].lower().strip(), [criterion['label'].lower().strip()])
        found = None
        # Experience/education/certification are deliberately not inferred from keyword matches.
        if criterion['category'] in ('skill', 'language', 'preferred'):
            for section in sections:
                if INJECTION.search(section['text']):
                    continue
                for term in terms:
                    match = re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', section['text'], re.I)
                    if match:
                        excerpt = section['text'][max(0, match.start() - 100):match.end() + 160]
                        # Negated phrases cannot substantiate an affirmative claim.
                        if re.search(r'\b(no|not|without|never|lack|learning|want to learn)\b', section['text'][max(0, match.start() - 45):match.start()], re.I):
                            continue
                        found = {'excerpt': excerpt, 'source': section['source']}
                        break
                if found:
                    break
        if found:
            matched += criterion['weight']
        evidence.append({'criterion': criterion['label'], 'mandatory': criterion['mandatory'], 'weight': criterion['weight'],
                         'status': 'Mention found — unverified' if found else 'Unknown — human verification required',
                         'excerpt': found['excerpt'] if found else '', 'source': found['source'] if found else '', 'confidence': 'unverified'})
    score = round(matched * 100 / total) if total and not suspicious else None
    # Baseline cannot assert that mandatory eligibility is met.
    return {'score': score, 'recommendation': 'Review Required', 'evidence': evidence, 'warnings': warnings}


def screen(application):
    criteria = list(application.job.criteria.order_by('created_at').values('label', 'category', 'mandatory', 'weight'))
    sections = []
    source_ids = []
    for extraction in Extraction.objects.filter(document__application=application, document__scan_status='clean').select_related('document'):
        source_ids.append(str(extraction.document_id))
        for section in extraction.sections:
            sections.append({'text': section['text'], 'source': f'Document {extraction.document_id} · {section["section"]}'})
    result = evaluate(criteria, sections)
    if not sections:
        result['score'] = None
        result['warnings'].append('No verified clean document extraction is available. Processing may be temporarily unavailable.')
    snapshot = {'version': application.job.policy_version, 'criteria': criteria}
    digest = hashlib.sha256(json.dumps({'policy': snapshot, 'sections': sections}, sort_keys=True).encode()).hexdigest()
    return ScreeningRun.objects.create(application=application, policy_snapshot=snapshot, source_ids=source_ids, input_hash=digest, **result)
