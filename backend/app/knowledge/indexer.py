"""Compatibility entry point; all indexing now uses durable fenced builds."""
from app.knowledge.build_pipeline import process_file
from app.knowledge.embedding import embedding_service
from app.knowledge.elasticsearch import elasticsearch_service
from app.knowledge.parser import parser_service
