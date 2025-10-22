"""
Test utilities and helper functions
"""
from faker import Faker
from app.models.document import DocumentCategory, UrgencyLevel, ProcessedDocument, DocumentMetadata
import random

fake = Faker(['de_DE', 'en_US'])


def generate_sample_document(category: DocumentCategory = None, urgency: UrgencyLevel = None):
    """Generate a random sample document for testing"""
    if category is None:
        category = random.choice(list(DocumentCategory))
    if urgency is None:
        urgency = random.choice(list(UrgencyLevel))

    return ProcessedDocument(
        raw_text=fake.text(max_nb_chars=500),
        category=category,
        urgency_level=urgency,
        metadata=DocumentMetadata(
            customer_id=f"CUST-{fake.random_number(digits=5)}",
            account_number=fake.iban(),
            email=fake.email(),
            phone=fake.phone_number(),
            subject=fake.sentence()
        ),
        extracted_info={
            "required_action": fake.sentence(),
            "key_points": [fake.sentence() for _ in range(3)],
            "mentioned_amounts": f"{fake.random_number(digits=5)} EUR",
            "reference_numbers": [f"REF-{fake.random_number(digits=4)}"]
        },
        confidence_score=random.uniform(0.7, 1.0),
        assigned_department=fake.company(),
        requires_immediate_attention=(urgency == UrgencyLevel.HIGH)
    )


def generate_loan_application_text():
    """Generate realistic loan application text"""
    return f"""
Sehr geehrte Damen und Herren,

ich möchte einen Kredit über {fake.random_number(digits=5)} Euro beantragen.
Meine Kundennummer ist: CUST-{fake.random_number(digits=5)}
Kontonummer: {fake.iban()}
Email: {fake.email()}
Telefon: {fake.phone_number()}

Bitte kontaktieren Sie mich bezüglich der nächsten Schritte.

Mit freundlichen Grüßen,
{fake.name()}
"""


def generate_complaint_text():
    """Generate realistic complaint text"""
    return f"""
URGENT COMPLAINT

Customer ID: CUST-{fake.random_number(digits=5)}
Account: {fake.iban()}

I am writing to complain about {fake.sentence()}
This issue requires immediate attention and resolution.

Please contact me at: {fake.email()}
Phone: {fake.phone_number()}

Regards,
{fake.name()}
"""


def generate_kyc_update_text():
    """Generate realistic KYC update text"""
    return f"""
KYC Document Update

Customer: {fake.name()}
Customer ID: CUST-{fake.random_number(digits=5)}
Account Number: {fake.iban()}

I am submitting updated identification documents as requested.
Please find attached my {fake.random_element(['passport', 'ID card', 'residence permit'])}.

Contact: {fake.email()}
Phone: {fake.phone_number()}

Best regards,
{fake.name()}
"""


def create_mock_embedding(dimension: int = 1024):
    """Create a mock embedding vector"""
    return [random.uniform(-1, 1) for _ in range(dimension)]


def assert_valid_processed_document(doc: ProcessedDocument):
    """Assert that a ProcessedDocument has all required fields"""
    assert doc.id is not None
    assert len(doc.id) > 0
    assert doc.raw_text is not None
    assert doc.category in DocumentCategory
    assert doc.urgency_level in UrgencyLevel
    assert isinstance(doc.metadata, DocumentMetadata)
    assert isinstance(doc.extracted_info, dict)
    assert 0 <= doc.confidence_score <= 1
    assert doc.assigned_department is not None
    assert isinstance(doc.requires_immediate_attention, bool)

