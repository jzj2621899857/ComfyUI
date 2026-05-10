"""
工作流版本化管理 - 支持工作流的版本控制和回滚
"""

import json
import hashlib
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class WorkflowVersion:
    version_id: str
    workflow_id: str
    workflow_data: Dict[str, Any]
    timestamp: float
    author: str = "system"
    description: str = ""
    tags: List[str] = field(default_factory=list)
    is_active: bool = False
    
    @property
    def created_at(self) -> str:
        return datetime.fromtimestamp(self.timestamp).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "workflow_id": self.workflow_id,
            "workflow_data": self.workflow_data,
            "timestamp": self.timestamp,
            "author": self.author,
            "description": self.description,
            "tags": self.tags,
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowVersion":
        return cls(**data)

class WorkflowVersionManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._versions: Dict[str, List[WorkflowVersion]] = {}
            cls._storage_path = None
            cls._enabled = False
        return cls._instance
    
    def enable(self, storage_path: str = None):
        self._enabled = True
        if storage_path:
            self._storage_path = storage_path
            os.makedirs(storage_path, exist_ok=True)
            self._load_from_storage()
    
    def disable(self):
        self._enabled = False
    
    def is_enabled(self) -> bool:
        return self._enabled
    
    def _generate_version_id(self, workflow_id: str, workflow_data: Dict) -> str:
        data_str = json.dumps(workflow_data, sort_keys=True)
        hash_str = hashlib.md5(data_str.encode()).hexdigest()[:16]
        timestamp = int(datetime.now().timestamp())
        return f"{workflow_id}-{timestamp}-{hash_str}"
    
    def save_version(self, workflow_id: str, workflow_data: Dict, description: str = "", tags: List[str] = None) -> str:
        if not self._enabled:
            return ""
        
        version_id = self._generate_version_id(workflow_id, workflow_data)
        
        if workflow_id not in self._versions:
            self._versions[workflow_id] = []
        
        version = WorkflowVersion(
            version_id=version_id,
            workflow_id=workflow_id,
            workflow_data=workflow_data,
            timestamp=datetime.now().timestamp(),
            description=description,
            tags=tags or []
        )
        
        self._versions[workflow_id].append(version)
        
        if self._storage_path:
            self._save_to_storage()
        
        return version_id
    
    def get_version(self, workflow_id: str, version_id: str) -> Optional[WorkflowVersion]:
        if workflow_id not in self._versions:
            return None
        
        for version in self._versions[workflow_id]:
            if version.version_id == version_id:
                return version
        
        return None
    
    def get_all_versions(self, workflow_id: str) -> List[WorkflowVersion]:
        if workflow_id not in self._versions:
            return []
        
        return sorted(self._versions[workflow_id], key=lambda v: v.timestamp, reverse=True)
    
    def get_latest_version(self, workflow_id: str) -> Optional[WorkflowVersion]:
        versions = self.get_all_versions(workflow_id)
        return versions[0] if versions else None
    
    def rollback_to_version(self, workflow_id: str, version_id: str) -> bool:
        version = self.get_version(workflow_id, version_id)
        if not version:
            return False
        
        for v in self._versions[workflow_id]:
            v.is_active = False
        
        version.is_active = True
        
        if self._storage_path:
            self._save_to_storage()
        
        return True
    
    def delete_version(self, workflow_id: str, version_id: str) -> bool:
        if workflow_id not in self._versions:
            return False
        
        original_count = len(self._versions[workflow_id])
        self._versions[workflow_id] = [
            v for v in self._versions[workflow_id]
            if v.version_id != version_id
        ]
        
        if self._storage_path:
            self._save_to_storage()
        
        return len(self._versions[workflow_id]) < original_count
    
    def _save_to_storage(self):
        if not self._storage_path:
            return
        
        for workflow_id, versions in self._versions.items():
            filepath = os.path.join(self._storage_path, f"{workflow_id}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump([v.to_dict() for v in versions], f, indent=2)
    
    def _load_from_storage(self):
        if not self._storage_path:
            return
        
        for filename in os.listdir(self._storage_path):
            if not filename.endswith('.json'):
                continue
            
            workflow_id = filename[:-5]
            filepath = os.path.join(self._storage_path, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._versions[workflow_id] = [WorkflowVersion.from_dict(v) for v in data]
            except Exception:
                pass
    
    def get_version_diff(self, workflow_id: str, version_id_1: str, version_id_2: str) -> Dict[str, Any]:
        v1 = self.get_version(workflow_id, version_id_1)
        v2 = self.get_version(workflow_id, version_id_2)
        
        if not v1 or not v2:
            return {}
        
        return {
            "from_version": v1.version_id,
            "to_version": v2.version_id,
            "from_timestamp": v1.created_at,
            "to_timestamp": v2.created_at,
            "nodes_added": [],
            "nodes_removed": [],
            "nodes_changed": []
        }

version_manager = WorkflowVersionManager()