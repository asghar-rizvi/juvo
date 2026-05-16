import pytest
from datetime import date
from src.agents.intent_agent import IntentAgent
from src.agents.discovery_agent import ProviderDiscoveryAgent
from src.agents.orchestrator import ServiceOrchestrator
from src.models import ServiceIntent, Language


class TestIntentAgent:
    """Test Intent Agent functionality"""
    
    def test_urdu_intent_extraction(self):
        """Test extracting intent from Roman Urdu"""
        agent = IntentAgent()
        
        result = agent.process_input_sync(
            "Mujhe kal subah G-13 mein AC technician chahiye"
        )
        
        assert result['status'] == 'success'
        intent = result['intent']
        assert 'AC' in intent.service_type.upper() or 'TECHNICIAN' in intent.service_type.upper()
        assert 'G-13' in intent.location.upper()
    
    def test_english_intent_extraction(self):
        """Test extracting intent from English"""
        agent = IntentAgent()
        
        result = agent.process_input_sync(
            "I need a plumber tomorrow morning in F-7 Islamabad"
        )
        
        assert result['status'] == 'success'
        intent = result['intent']
        assert 'plumber' in intent.service_type.lower()
        assert 'F-7' in intent.location


class TestProviderDiscovery:
    """Test Provider Discovery Agent"""
    
    def test_find_providers(self):
        """Test finding providers near location"""
        agent = ProviderDiscoveryAgent()
        
        intent = ServiceIntent(
            service_type="AC Technician",
            location="G-13, Islamabad",
            preferred_date=date.today(),
            language_detected=Language.ENGLISH
        )
        
        result = agent.find_and_rank_providers_sync(
            intent=intent,
            session_id="test-session"
        )
        
        assert result['status'] == 'success'
        assert len(result['providers']) > 0
        assert result['providers'][0].distance_km <= 15.0


class TestOrchestrator:
    """Test complete workflow orchestration"""
    
    def test_complete_workflow(self):
        """Test end-to-end workflow"""
        orchestrator = ServiceOrchestrator()
        
        result = orchestrator.handle_service_request_sync(
            user_input="Mujhe kal G-13 mein AC technician chahiye",
            user_phone="+923001234567",
            auto_book=False
        )
        
        assert result['status'] in ['providers_found', 'completed_with_booking']
        assert 'intent' in result['steps']
        assert 'discovery' in result['steps']
    
    def test_auto_booking_workflow(self):
        """Test workflow with auto-booking"""
        orchestrator = ServiceOrchestrator()
        
        result = orchestrator.handle_service_request_sync(
            user_input="Need plumber tomorrow in F-7",
            user_phone="+923009876543",
            user_name="Test User",
            auto_book=True
        )
        
        if result['status'] == 'completed_with_booking':
            assert 'booking' in result['steps']
            assert 'followup' in result['steps']
            assert result['booking_reference'].startswith('BK')


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])