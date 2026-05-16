import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import json
from pythonjsonlogger import jsonlogger
from logging.handlers import RotatingFileHandler

from config import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.utcnow().isoformat()
        
        log_record['environment'] = settings.APP_ENV
        
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname


class ColoredConsoleFormatter(logging.Formatter):    
    COLORS = {
        'DEBUG': '\033[36m',      
        'INFO': '\033[32m',       
        'WARNING': '\033[33m',    
        'ERROR': '\033[31m',      
        'CRITICAL': '\033[35m',   
        'RESET': '\033[0m'
    }
    
    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        formatted = super().format(record)
        
        return formatted + self.COLORS['RESET']


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Setup application logging with file and console handlers
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (default: logs/app_{date}.log)
    
    Returns:
        Configured logger instance
    """
    level = log_level or settings.LOG_LEVEL
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    if log_file is None:
        log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    else:
        log_file = Path(log_file)
    
    logger = logging.getLogger('service_orchestrator')
    logger.setLevel(numeric_level)
    
    logger.handlers.clear()
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    console_format = ColoredConsoleFormatter(
        fmt='%(levelname)-8s | %(asctime)s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024, 
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(numeric_level)
    
    json_format = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s %(pathname)s %(lineno)d'
    )
    file_handler.setFormatter(json_format)
    logger.addHandler(file_handler)
    
    error_file = log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
    error_handler = RotatingFileHandler(
        filename=error_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(json_format)
    logger.addHandler(error_handler)
    
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('google').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    logger.info(f"Logging initialized - Level: {level}, File: {log_file}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(f'service_orchestrator.{name}')


main_logger = setup_logging()


class AgentLogger:
    """
    Specialized logger for agent interactions
    Logs decisions, tool calls, and reasoning
    """
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.logger = get_logger(f'agent.{agent_name}')
    
    def log_decision(
        self,
        decision: dict,
        reasoning: str,
        confidence: Optional[float] = None,
        metadata: Optional[dict] = None
    ):
        """Log agent decision with reasoning"""
        log_data = {
            'agent': self.agent_name,
            'event': 'decision',
            'decision': decision,
            'reasoning': reasoning,
            'confidence': confidence,
            'metadata': metadata or {}
        }
        self.logger.info(f"Decision: {json.dumps(log_data, ensure_ascii=False)}")
    
    def log_tool_call(
        self,
        tool_name: str,
        inputs: dict,
        outputs: Optional[dict] = None,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Log tool/function call"""
        log_data = {
            'agent': self.agent_name,
            'event': 'tool_call',
            'tool': tool_name,
            'inputs': inputs,
            'outputs': outputs,
            'success': success,
            'error': error
        }
        
        if success:
            self.logger.info(f"Tool call: {tool_name} - SUCCESS")
            self.logger.debug(f"Tool details: {json.dumps(log_data, ensure_ascii=False)}")
        else:
            self.logger.error(f"Tool call: {tool_name} - FAILED: {error}")
    
    def log_workflow_step(
        self,
        step_name: str,
        status: str,
        data: Optional[dict] = None
    ):
        """Log workflow progression"""
        log_data = {
            'agent': self.agent_name,
            'event': 'workflow_step',
            'step': step_name,
            'status': status,
            'data': data or {}
        }
        self.logger.info(f"Workflow: {step_name} - {status}")
        self.logger.debug(f"Step details: {json.dumps(log_data, ensure_ascii=False)}")
    
    def log_error(
        self,
        error_type: str,
        error_message: str,
        context: Optional[dict] = None
    ):
        """Log error with context"""
        log_data = {
            'agent': self.agent_name,
            'event': 'error',
            'error_type': error_type,
            'error_message': error_message,
            'context': context or {}
        }
        self.logger.error(f"Error: {error_type} - {error_message}")
        self.logger.debug(f"Error context: {json.dumps(log_data, ensure_ascii=False)}")


__all__ = ['setup_logging', 'get_logger', 'AgentLogger', 'main_logger']