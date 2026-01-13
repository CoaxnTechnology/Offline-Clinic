"""
DICOM Listener - Standalone script to start DICOM servers
Can be run independently or integrated with Flask app
"""
import os
import sys
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.services.dicom_service import start_dicom_servers, get_server_status

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("dicom_listener.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main function to start DICOM listener"""
    logger.info("Starting DICOM Listener...")
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        # Start DICOM servers
        logger.info("Initializing DICOM servers...")
        start_dicom_servers()
        
        # Get and display status
        status = get_server_status()
        logger.info("=" * 60)
        logger.info("DICOM Servers Status:")
        logger.info(f"  MWL Server: {'Running' if status['mwl_server_running'] else 'Stopped'}")
        logger.info(f"  MWL Port: {status['mwl_port']}")
        logger.info(f"  Storage Server: {'Running' if status['storage_server_running'] else 'Stopped'}")
        logger.info(f"  Storage Port: {status['storage_port']}")
        logger.info(f"  AE Title: {status['ae_title']}")
        logger.info("=" * 60)
        logger.info("DICOM servers are running. Press Ctrl+C to stop.")
        
        # Keep the script running
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nShutting down DICOM servers...")
            logger.info("DICOM Listener stopped.")


if __name__ == '__main__':
    main()
