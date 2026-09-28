"""
Neo4j Database Client and Connection Manager.
Handles session management, Cypher transaction execution, and health checks.
"""

from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase, Driver, Session
from config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Neo4jClient:
    """Manages connections and transactions to the Neo4j database."""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        self.uri = uri or settings.NEO4J_URI
        self.user = user or settings.NEO4J_USER
        self.password = password or settings.NEO4J_PASSWORD
        self.database = database or settings.NEO4J_DATABASE
        self._driver: Optional[Driver] = None

    def connect(self) -> Driver:
        """Initialize and verify connection to Neo4j."""
        if self._driver is None:
            logger.info(f"Connecting to Neo4j at {self.uri} as {self.user}...")
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
        return self._driver

    def close(self) -> None:
        """Close Neo4j driver connection."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed.")

    def check_connection(self) -> Dict[str, Any]:
        """Verify connectivity and return Neo4j version and APOC status."""
        driver = self.connect()
        with driver.session(database=self.database) as session:
            # Check basic connectivity and version
            server_info = driver.get_server_info()
            
            # Check APOC availability
            apoc_installed = False
            try:
                result = session.run("RETURN apoc.version() AS version")
                record = result.single()
                if record:
                    apoc_installed = True
            except Exception:
                apoc_installed = False

            return {
                "connected": True,
                "server_agent": server_info.agent,
                "protocol_version": server_info.protocol_version,
                "database": self.database,
                "apoc_installed": apoc_installed,
            }

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a read/write Cypher query and return list of dictionary records."""
        driver = self.connect()
        with driver.session(database=self.database) as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a write transaction and return summary counters."""
        driver = self.connect()
        with driver.session(database=self.database) as session:
            result = session.run(query, parameters or {})
            summary = result.consume()
            return {
                "nodes_created": summary.counters.nodes_created,
                "nodes_deleted": summary.counters.nodes_deleted,
                "relationships_created": summary.counters.relationships_created,
                "relationships_deleted": summary.counters.relationships_deleted,
                "properties_set": summary.counters.properties_set,
            }

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Singleton client instance
neo4j_client = Neo4jClient()
