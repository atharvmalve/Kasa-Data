from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from app.db.models import DataPack, Document
from app.schemas.datapack import DataPackCreate, DataPackUpdate, DataPackResponse


class DataPackService:
    @staticmethod
    def create(db: Session, data: DataPackCreate) -> DataPack:
        datapack = DataPack(
            name=data.name.strip(),
            description=data.description.strip() if data.description else None
        )
        db.add(datapack)
        db.commit()
        db.refresh(datapack)
        return datapack

    @staticmethod
    def get(db: Session, datapack_id: UUID) -> Optional[DataPack]:
        return db.query(DataPack).filter(DataPack.id == datapack_id).first()

    @staticmethod
    def list_all(db: Session) -> List[DataPackResponse]:
        # Query datapacks with file counts and aggregate status
        datapacks = db.query(DataPack).order_by(DataPack.created_at.desc()).all()
        results: List[DataPackResponse] = []

        for dp in datapacks:
            docs = db.query(Document).filter(Document.datapack_id == dp.id).all()
            file_count = len(docs)
            
            # Aggregate status
            statuses = [d.processing_status for d in docs]
            agg_status = "empty"
            if file_count > 0:
                if any(s == "processing" for s in statuses):
                    agg_status = "processing"
                elif any(s == "failed" for s in statuses):
                    agg_status = "has_failures"
                elif any(s == "partially_processed" for s in statuses):
                    agg_status = "partially_processed"
                elif all(s == "processed" for s in statuses):
                    agg_status = "processed"
                else:
                    agg_status = "pending"

            results.append(DataPackResponse(
                id=dp.id,
                name=dp.name,
                description=dp.description,
                created_at=dp.created_at,
                updated_at=dp.updated_at,
                file_count=file_count,
                processing_status=agg_status
            ))

        return results

    @staticmethod
    def update(db: Session, datapack_id: UUID, data: DataPackUpdate) -> Optional[DataPack]:
        datapack = db.query(DataPack).filter(DataPack.id == datapack_id).first()
        if not datapack:
            return None

        if data.name is not None:
            datapack.name = data.name.strip()
        if data.description is not None:
            datapack.description = data.description.strip() if data.description else None

        db.commit()
        db.refresh(datapack)
        return datapack

    @staticmethod
    def delete(db: Session, datapack_id: UUID) -> bool:
        datapack = db.query(DataPack).filter(DataPack.id == datapack_id).first()
        if not datapack:
            return False
        db.delete(datapack)
        db.commit()
        return True

