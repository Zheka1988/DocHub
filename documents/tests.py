
import json
import io
import zipfile
from unittest.mock import MagicMock, patch

from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from users.models import User, Department, Role
from .models import Document, Source, Direction
from .admin import DocumentAdmin
from .forms import DocumentAdminForm

class DocumentFolderUploadTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.site = AdminSite()
        
        self.dept = Department.objects.create(title="IT_Dept")
        self.user = User.objects.create(
            username="testuser", 
            department=self.dept,
            role=Role.USER.name
        )
        self.user.set_password("password")
        self.user.save()
        
        self.source = Source.objects.create(title="Test Source")
        self.direction = Direction.objects.create(title="Test Direction")

    @patch("documents.admin.get_minio_client")
    def test_save_model_folder_upload(self, mock_get_client):
        # Setup MinIO mock
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.bucket_exists.return_value = True

        # Setup Admin and Object
        admin = DocumentAdmin(Document, self.site)
        doc = Document(
            title="Test Doc",
            number="123",
            date=timezone.now().date(),
            realization="Test",
            grade=100,
            executor=self.user,
            source=self.source,
            direction=self.direction
        )

        # Mock Files
        file1 = SimpleUploadedFile("file1.txt", b"content1", content_type="text/plain")
        file2 = SimpleUploadedFile("file2.txt", b"content2", content_type="text/plain")
        
        # Mock Request
        request = self.factory.post("/admin/documents/document/add/")
        request.FILES.setlist("file", [file1, file2])
        
        # Mock file_paths JSON
        paths = [
            {"name": "file1.txt", "path": "Root/file1.txt"},
            {"name": "file2.txt", "path": "Root/Sub/file2.txt"}
        ]
        request.POST = request.POST.copy()
        request.POST["file_paths"] = json.dumps(paths)
        
        form = DocumentAdminForm(request.POST, request.FILES, instance=doc)
        
        admin.save_model(request, doc, form, change=False)
        
        # Verify DB
        self.assertEqual(doc.content_type, "folder")
        self.assertEqual(doc.original_filename, "Root")
        self.assertEqual(doc.size_bytes, len(b"content1") + len(b"content2"))
        self.assertTrue(doc.storage_key.startswith("IT_Dept/"))
        self.assertTrue(doc.storage_key.endswith("/"))
        
        # Verify MinIO calls
        prefix = doc.storage_key
        expected_key1 = prefix + "Root/file1.txt"
        expected_key2 = prefix + "Root/Sub/file2.txt"
        
        self.assertEqual(mock_client.put_object.call_count, 2)
        
        call_args_list = mock_client.put_object.call_args_list
        keys_uploaded = [c[1]['object_name'] for c in call_args_list]
        self.assertIn(expected_key1, keys_uploaded)
        self.assertIn(expected_key2, keys_uploaded)

    @patch("documents.views.get_minio_client")
    def test_document_open_zip(self, mock_get_client):
        # Setup MinIO mock
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Setup Document
        doc = Document.objects.create(
            title="Zip Doc",
            number="999",
            date=timezone.now().date(),
            realization="Test",
            grade=50,
            executor=self.user,
            source=self.source,
            direction=self.direction,
            storage_key="IT_Dept/2026/01/uuid/",
            original_filename="MyFolder",
            content_type="folder"
        )
        
        # Mock list_objects return
        MockObj = MagicMock
        obj1 = MockObj()
        obj1.object_name = "IT_Dept/2026/01/uuid/MyFolder/f1.txt"
        obj2 = MockObj()
        obj2.object_name = "IT_Dept/2026/01/uuid/MyFolder/Sub/f2.txt"
        
        mock_client.list_objects.return_value = [obj1, obj2]
        
        # Mock get_object return
        def get_object_side_effect(bucket, object_name):
            resp = MagicMock()
            if object_name.endswith("f1.txt"):
                resp.read.return_value = b"data1"
            else:
                resp.read.return_value = b"data2"
            return resp
            
        mock_client.get_object.side_effect = get_object_side_effect
        
        # Make request
        self.client.force_login(self.user)
        url = reverse("document_open", args=[doc.pk])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/zip")
        self.assertIn('attachment; filename="MyFolder.zip"', response.headers["Content-Disposition"])
        
        # Check content
        content = b"".join(response.streaming_content) if hasattr(response, 'streaming_content') else response.content
        
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            # Note: zipfile normalization might use / or \ on windows? standard is /
            # We put relative paths "MyFolder/f1.txt" etc.
            self.assertIn("MyFolder/f1.txt", z.namelist())
            self.assertIn("MyFolder/Sub/f2.txt", z.namelist())
            self.assertEqual(z.read("MyFolder/f1.txt"), b"data1")
