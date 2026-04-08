"""
Bootstrap script – run once on first startup to create the workbook and folders.
Called automatically by main.py on startup.
"""
import logging

from config import settings

logger = logging.getLogger(__name__)


def bootstrap() -> None:
    # Create required directories (all absolute paths from config)
    dirs = [
        settings.data_dir,
        settings.receipts_dir,
        settings.receipts_dir / "unassigned",
        settings.data_dir / "tmp_uploads",
        settings.static_dir,
        settings.templates_dir,
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        logger.debug("Directory ready: %s", d)

    # Bootstrap the Excel workbook
    from app.services.workbook_service import workbook_service
    workbook_service.bootstrap()
    logger.info("Bootstrap complete. Workbook: %s", settings.workbook_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bootstrap()
    print("Bootstrap complete.")
