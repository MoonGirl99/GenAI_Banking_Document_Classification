import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict
import json
from app.models.document import ProcessedDocument, UrgencyLevel
from app.config import settings


class RoutingService:
    def __init__(self):
        self.department_mapping = settings.DEPARTMENT_EMAILS

    async def route_document(self, document: ProcessedDocument) -> Dict:
        """
        Route document to appropriate department and create alerts
        """
        routing_result = {
            "document_id": document.id,
            "department": document.assigned_department,
            "urgency": document.urgency_level,
            "alerts_created": []
        }

        # Create high priority alert if needed
        if document.requires_immediate_attention:
            alert = await self._create_priority_alert(document)
            routing_result["alerts_created"].append(alert)

        # Send notification to department
        notification_sent = await self._notify_department(document)
        routing_result["notification_sent"] = notification_sent

        # Log routing decision
        await self._log_routing(document, routing_result)

        return routing_result

    async def _create_priority_alert(self, document: ProcessedDocument) -> Dict:
        """
        Create priority alert for high urgency documents
        """
        alert = {
            "type": "HIGH_PRIORITY",
            "document_id": document.id,
            "category": document.category,
            "customer_id": document.metadata.customer_id,
            "reason": self._determine_alert_reason(document),
            "created_at": document.processed_at.isoformat()
        }

        # In production, this would integrate with alerting system
        # For now, we'll just return the alert structure
        return alert

    async def _notify_department(self, document: ProcessedDocument) -> bool:
        """
        Send notification to the assigned department
        """
        try:
            # Create email notification
            subject = f"[{document.urgency_level.upper()}] New {document.category} - Customer: {document.metadata.customer_id or 'Unknown'}"

            body = self._create_notification_body(document)

            # In production, integrate with email service
            # For now, return success
            return True

        except Exception as e:
            print(f"Failed to notify department: {str(e)}")
            return False

    def _create_notification_body(self, document: ProcessedDocument) -> str:
        """Create email body for department notification"""
        return f"""
        New Document Received
        =====================

        Category: {document.category}
        Urgency: {document.urgency_level}
        Customer ID: {document.metadata.customer_id or 'Not identified'}
        Account Number: {document.metadata.account_number or 'Not identified'}

        Required Action:
        {document.extracted_info.get('required_action', 'Review required')}

        Key Points:
        {json.dumps(document.extracted_info.get('key_points', []), indent=2)}

        Document ID: {document.id}
        Processed: {document.processed_at.isoformat()}
        Confidence Score: {document.confidence_score:.2f}

        ---
        Access the full document in the system using ID: {document.id}
        """

    def _determine_alert_reason(self, document: ProcessedDocument) -> str:
        """Determine the reason for high priority alert"""
        reasons = []

        if document.urgency_level == UrgencyLevel.HIGH:
            reasons.append("High urgency classification")

        if "complaint" in document.category.lower():
            reasons.append("Customer complaint")

        if document.extracted_info.get("fraud_risk"):
            reasons.append("Potential fraud risk")

        return " | ".join(reasons) if reasons else "Manual review required"

    async def _log_routing(self, document: ProcessedDocument, routing_result: Dict):
        """Log routing decision for audit trail"""
        # In production, this would write to audit log
        print(f"Document {document.id} routed to {routing_result['department']}")