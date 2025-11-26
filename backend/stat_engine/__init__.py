"""
Stat Engine - Production-Grade Statistics Aggregation Microservice

Aggregates fight event data into normalized statistics for:
- Round-level stats
- Fight-level stats  
- Career-level stats

CRITICAL: This service ONLY reads from existing events table.
It NEVER creates events. All stats are derived from judge logging.
"""
