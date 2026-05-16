from typing import Dict, Any, Optional
import uuid

from src.models import ServiceIntent, ProviderMatch
from src.agents.intent_agent import IntentAgent
from src.agents.discovery_agent import ProviderDiscoveryAgent
from src.agents.booking_agent import BookingAgent
from src.agents.followup_agent import FollowUpAgent
from src.utils.logger import AgentLogger
from src.database.connection import get_db
from src.tools import DatabaseTools


class ServiceOrchestrator:
    """
    Main orchestrator coordinating all agents
    Implements complete service request lifecycle
    """
    
    def __init__(self):
        self.name = "ServiceOrchestrator"
        self.logger = AgentLogger(self.name)
        
        # Initialize all agents
        self.intent_agent = IntentAgent()
        self.discovery_agent = ProviderDiscoveryAgent()
        self.booking_agent = BookingAgent()
        self.followup_agent = FollowUpAgent()
        
        self.logger.log_workflow_step(
            "orchestrator_init",
            "completed",
            {"agents_initialized": 4}
        )
    
    async def handle_service_request(
        self,
        user_input: str,
        user_phone: str,
        user_name: Optional[str] = None,
        session_id: Optional[str] = None,
        auto_book: bool = False
    ) -> Dict[str, Any]:
        """
        Handle complete service request workflow
        
        Workflow:
        1. Understand Intent (IntentAgent)
        2. Find Providers (ProviderDiscoveryAgent)
        3. Present Options to User
        4. [Optional] Auto-book with top provider
        
        Args:
            user_input: User's natural language request
            user_phone: User's phone number
            user_name: User's name
            session_id: Session ID (generated if not provided)
            auto_book: Automatically book with top provider
        
        Returns:
            Complete workflow result
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        self.logger.log_workflow_step(
            "service_request",
            "started",
            {
                "user_input_preview": user_input[:100],
                "session_id": session_id,
                "auto_book": auto_book
            }
        )
        
        workflow_result = {
            'session_id': session_id,
            'steps': {},
            'status': 'in_progress'
        }
        
        try:
            # ============================================
            # STEP 1: Intent Understanding
            # ============================================
            self.logger.log_workflow_step("step_1_intent", "started", {})
            
            intent_result = await self.intent_agent.process_input(
                user_input=user_input,
                session_id=session_id
            )
            
            intent: ServiceIntent = intent_result['intent']
            workflow_result['steps']['intent'] = {
                'status': 'completed',
                'data': intent.model_dump(mode='json')
            }
            
            self.logger.log_decision(
                {
                    "service": intent.service_type,
                    "location": intent.location,
                    "date": intent.preferred_date.isoformat()
                },
                "Successfully extracted service intent from user input",
                confidence=0.9
            )
            
            # ============================================
            # STEP 2: Provider Discovery & Ranking
            # ============================================
            self.logger.log_workflow_step("step_2_discovery", "started", {})
            
            discovery_result = await self.discovery_agent.find_and_rank_providers(
                intent=intent,
                session_id=session_id,
                max_distance_km=15.0,
                max_results=5
            )
            
            if discovery_result['status'] == 'no_providers_found':
                workflow_result['status'] = 'no_providers_available'
                workflow_result['message'] = discovery_result['message']
                
                self.logger.log_workflow_step(
                    "service_request",
                    "completed_no_providers",
                    {}
                )
                
                return workflow_result
            
            providers: list[ProviderMatch] = discovery_result['providers']
            workflow_result['steps']['discovery'] = {
                'status': 'completed',
                'provider_count': len(providers),
                'providers': [p.model_dump(mode='json') for p in providers],
                'location': discovery_result['location'],
                'ranking_reasoning': discovery_result['ranking']['reasoning']
            }
            
            self.logger.log_decision(
                {
                    "provider_count": len(providers),
                    "top_provider": providers[0].name if providers else None
                },
                f"Found and ranked {len(providers)} providers",
                confidence=discovery_result['ranking']['confidence_score'] / 100.0
            )
            
            # ============================================
            # STEP 3: Present Options / Auto-Book
            # ============================================
            if auto_book and providers:
                self.logger.log_workflow_step(
                    "step_3_auto_booking",
                    "started",
                    {"selected_provider": providers[0].name}
                )
                
                # Auto-book with top provider
                booking_result = await self.booking_agent.create_booking(
                    intent=intent,
                    selected_provider=providers[0],
                    user_phone=user_phone,
                    user_name=user_name,
                    session_id=session_id,
                    location_coords=(
                        discovery_result['location']['latitude'],
                        discovery_result['location']['longitude']
                    )
                )
                
                if booking_result['status'] == 'success':
                    workflow_result['steps']['booking'] = {
                        'status': 'completed',
                        'booking': booking_result['booking'].model_dump(mode='json')
                    }
                    
                    # Schedule follow-up reminder
                    reminder_result = self.followup_agent.schedule_reminder(
                        booking_id=booking_result['booking'].booking_id,
                        session_id=session_id,
                        hours_before=1
                    )
                    
                    workflow_result['steps']['followup'] = {
                        'status': 'scheduled',
                        'reminder': reminder_result
                    }
                    
                    workflow_result['status'] = 'completed_with_booking'
                    workflow_result['booking_reference'] = booking_result['booking'].booking_reference
                    
                    self.logger.log_decision(
                        {
                            "booking_reference": booking_result['booking'].booking_reference,
                            "provider": providers[0].name
                        },
                        "Auto-booking completed successfully",
                        confidence=1.0
                    )
                else:
                    workflow_result['steps']['booking'] = {
                        'status': 'failed',
                        'reason': booking_result.get('message', 'Unknown error')
                    }
                    workflow_result['status'] = 'booking_failed'
            else:
                # Just present options
                workflow_result['status'] = 'providers_found'
                workflow_result['message'] = f"Found {len(providers)} providers. Please select one to book."
            
            # ============================================
            # Final Logging
            # ============================================
            self.logger.log_workflow_step(
                "service_request",
                "completed",
                {
                    "final_status": workflow_result['status'],
                    "steps_completed": len(workflow_result['steps'])
                }
            )
            
            # Log complete workflow to database
            with get_db() as db:
                tools = DatabaseTools(db)
                tools.log_conversation(
                    session_id=session_id,
                    agent_name=self.name,
                    agent_response=f"Workflow completed: {workflow_result['status']}",
                    metadata={
                        "workflow_steps": list(workflow_result['steps'].keys()),
                        "provider_count": len(providers) if providers else 0,
                        "auto_book": auto_book
                    },
                    reasoning="Complete service request workflow executed"
                )
            
            return workflow_result
            
        except Exception as e:
            self.logger.log_error(
                "workflow_error",
                str(e),
                {
                    "session_id": session_id,
                    "completed_steps": list(workflow_result['steps'].keys())
                }
            )
            
            workflow_result['status'] = 'error'
            workflow_result['error'] = str(e)
            
            return workflow_result
    
    def handle_service_request_sync(self, **kwargs) -> Dict[str, Any]:
        """Synchronous version of handle_service_request"""
        import asyncio
        return asyncio.run(self.handle_service_request(**kwargs))
    
    def shutdown(self):
        """Shutdown orchestrator and all agents"""
        self.followup_agent.shutdown()
        self.logger.log_workflow_step("orchestrator_shutdown", "completed", {})