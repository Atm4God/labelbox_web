import os
import uuid

import labelbox as lb
import requests
from django.conf import settings
from django.core.files.base import ContentFile

from .models import AnnotationProject, AnnotationTask, Annotation, Classification
from .models import ExportedAnnotation


class LabelboxService:
    """
    Service class to handle Labelbox-like operations and annotations
    """

    def __init__(self):
        self.client = lb.Client(api_key=settings.LABELBOX_API_KEY)

    def get_existing_data_row_keys(self, project_id):
        """
        Retrieve existing data row global keys for a specific project by filtering datasets.

        :param project_id: The ID of the Labelbox project.
        :return: List of existing data row global keys.
        """
        # Get the project using the provided project_id
        project = self.client.get_project(project_id)

        # Retrieve all datasets in the account
        datasets = self.client.get_datasets()

        # Initialize an empty list to store global keys
        global_keys = []

        # Iterate through all datasets
        for dataset in datasets:
            # Filter data rows linked to the given project
            for data_row in dataset.data_rows():
                if data_row.project().id == project_id:  # Ensure the data row belongs to the project
                    global_keys.append(data_row.global_key)

        return global_keys

    def check_dataRow_exists(self, global_key, project_id):
        """
        Check if the DataRow specified by the global_key exists in the project specified by project_id.
        """

        # Get project by project_id
        project = self.client.get_project(project_id)

        # Get datasets associated with the project
        datasets = self.client.get_datasets()
        # Loop over each dataset in the project
        for dataset in datasets:

            # For each dataset, get all the DataRow objects
            for dataRow in dataset.data_rows():
                # print('row',  dataRow)

                # check if the global_key of the current DataRow matches the one you are looking for
                if dataRow.global_key == global_key:
                    return True

        # If loop finishes without finding the DataRow then it does not exist in the project
        return False

    def get_ontology(self, project_id):
        """
        Fetches the ontology for a specific Labelbox project.

        :param project_id: The ID of the Labelbox project.
        :return: The Ontology object for the project.
        """
        project = self.client.get_project(project_id)
        ontology = project.ontology()
        return ontology

    def create_project(self, name, description, media_type='IMAGE'):
        """Create a new annotation project"""
        # Create Labelbox project
        lb_project = self.client.create_project(
            name=name,
            description=description,
            media_type=lb.MediaType.Image
        )

        # Create Django project
        project = AnnotationProject.objects.create(
            name=name,
            description=description,
            media_type=media_type,
            lb_uid=lb_project.uid
        )

        return project, lb_project

    def import_data_rows(self, project, image_urls, lb_project):
        """Import data rows for annotation"""
        uploads = []
        global_keys = []

        for image_url in image_urls:
            gb_key = f"TEST-ID-{uuid.uuid1()}"
            uploads.append({
                "row_data": image_url,
                "global_key": gb_key
            })
            global_keys.append(gb_key)

            # Create Django annotation task
            AnnotationTask.objects.create(
                project=project,
                global_key=gb_key,
                image_url=image_url
            )

        # Create dataset in Labelbox
        dataset = self.client.create_dataset(name=f"{project.name}-dataset")
        task = dataset.create_data_rows(uploads)
        task.wait_till_done()

        # Log task errors if any
        if task.errors:
            print(f"Data row upload errors: {task.errors}")
        print("Failed data rows:", task.failed_data_rows)

        # Link dataset to the project
        data_rows = list(dataset.data_rows())

        return global_keys

    def create_ontology(self, project):
        """Create ontology for a project with all supported annotation types"""
        ontology_builder = lb.OntologyBuilder(
            classifications=[
                lb.Classification(
                    class_type=lb.Classification.Type.RADIO,
                    name="radio_question",
                    options=[lb.Option(value="option1"), lb.Option(value="option2")]
                ),
                lb.Classification(
                    class_type=lb.Classification.Type.CHECKLIST,
                    name="checklist_question",
                    options=[lb.Option(value="option1"), lb.Option(value="option2")]
                ),
                lb.Classification(
                    class_type=lb.Classification.Type.TEXT,
                    name="text_question"
                )
            ],
            tools=[
                lb.Tool(tool=lb.Tool.Type.BBOX, name="bounding_box"),
                lb.Tool(tool=lb.Tool.Type.POLYGON, name="polygon"),
                lb.Tool(tool=lb.Tool.Type.POINT, name="point"),
                lb.Tool(tool=lb.Tool.Type.LINE, name="line"),
                lb.Tool(tool=lb.Tool.Type.RELATIONSHIP, name="relationship")
            ]
        )

        # Create Labelbox ontology
        ontology = self.client.create_ontology(
            f"{project.name}-ontology",
            ontology_builder.asdict()
        )

        # Attach ontology to Labelbox project
        lb_project = self.client.get_project(project.uid)
        lb_project.connect_ontology(ontology)

        return ontology

    def create_annotation(self, task_id, annotation_data):
        """Create annotation and sync with Labelbox"""
        task = AnnotationTask.objects.get(id=task_id)

        # Create annotation in Django
        annotation = Annotation.objects.create(
            task=task,
            annotation_type=annotation_data['annotation_type'],
            name=annotation_data['name'],
            data=annotation_data['data']
        )

        # Create classifications if any
        if 'classifications' in annotation_data:
            for class_data in annotation_data['classifications']:
                Classification.objects.create(
                    annotation=annotation,
                    name=class_data['name'],
                    classification_type=class_data['type'],
                    value=class_data['value']
                )

        # Convert to Labelbox format and upload
        lb_annotation = self._convert_to_labelbox_format(annotation)
        self._upload_to_labelbox(task.global_key, lb_annotation)

        return annotation

    def _convert_to_labelbox_format(self, annotation):
        """Convert Django annotation to Labelbox format"""
        lb_format = {
            "name": annotation.name + "-ontology",
            "dataRow": {"globalKey": annotation.task.global_key}
        }

        # Convert based on annotation type
        if annotation.annotation_type == 'BBOX':
            lb_format.update({
                "bbox": {
                    "top": annotation.data['top'],
                    "left": annotation.data['left'],
                    "height": annotation.data['height'],
                    "width": annotation.data['width']
                }
            })
        # Add other annotation type conversions here

        return lb_format


class ExportService(LabelboxService):
    def export_annotations(self, project_id):
        # Retrieve the project
        project = self.client.get_project(project_id)

        # Set export parameters
        export_params = {
            "attachments": True,
            "metadata_fields": True,
            "data_row_details": True,
            "project_details": True,
            "label_details": True,
        }
        filters = {
            "workflow_status": "Done"  # Only export completed tasks
        }

        # Start export task
        export_task = project.export_v2(params=export_params)
        export_task.wait_till_done()

        if export_task.errors:
            raise Exception(f"Export errors: {export_task.errors}")

        # Process exported JSON
        annotations = export_task.result
        for annotation in annotations:
            self._process_annotation(annotation)

    def _process_annotation(self, annotation):
        # Extract relevant data row details
        data_row = annotation["data_row"]
        task_id = data_row["id"]
        image_url = data_row["row_data"]

        # Extract annotation details
        project_details = next(iter(annotation["projects"].values()))
        labels = project_details.get("labels", [])
        annotations = []

        for label in labels:
            annotation_objects = label.get("annotations", {}).get("objects", [])
            for obj in annotation_objects:
                annotation_name = obj["name"]
                annotation_type = obj["annotation_kind"]
                annotation_data = obj  # Complete object data for JSONField

                # Append annotation to the list
                annotations.append({
                    "annotation_name": annotation_name,
                    "annotation_type": annotation_type,
                    "annotation_data": annotation_data
                })

        # Download the image
        response = requests.get(image_url)
        if response.status_code == 200:
            image_content = ContentFile(response.content)
            image_name = os.path.basename(image_url)

            # Save each annotation in the database
            for annotation in annotations:
                ExportedAnnotation.objects.create(
                    task_id=task_id,
                    annotation_name=annotation["annotation_name"],
                    annotation_type=annotation["annotation_type"],
                    annotation_data=annotation["annotation_data"],
                    image_file=image_content
                )
