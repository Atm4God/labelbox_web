import json
import uuid

import labelbox as lb
import labelbox.types as lb_types
from django.db import transaction
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, CreateView
from django.shortcuts import redirect, render, get_object_or_404
from django.http import JsonResponse

from .models import AnnotationTask, Annotation, Classification, AnnotationProject
from .services import ExportService
from .services import LabelboxService


class AnnotationProjectListView(ListView):
    model = AnnotationProject
    template_name = 'annotation/project_list.html'
    context_object_name = 'projects'


class AnnotationProjectCreateView(CreateView):
    model = AnnotationProject
    template_name = 'annotation/project_create.html'
    fields = ['name', 'description', 'media_type']
    success_url = reverse_lazy('project_list')

    def form_valid(self, form):
        with transaction.atomic():
            labelbox_service = LabelboxService()
            project, lb_project = labelbox_service.create_project(
                name=form.cleaned_data['name'],
                description=form.cleaned_data['description'],
                media_type=form.cleaned_data['media_type']
            )

            # Create ontology with all supported annotation types
            labelbox_service.create_ontology(lb_project)

            # Import images
            image_urls = self.request.POST.getlist('image_urls')
            labelbox_service.import_data_rows(project, image_urls, lb_project)

            return redirect(self.success_url)


class AnnotationTaskListView(ListView):
    model = AnnotationTask
    template_name = 'annotation/task_list.html'
    context_object_name = 'tasks'

    def get_queryset(self):
        project_id = self.kwargs.get('project_id')
        return AnnotationTask.objects.filter(project_id=project_id)


class AnnotationTaskDetailView(DetailView):
    model = AnnotationTask
    template_name = 'annotation/task_detail.html'
    context_object_name = 'task'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['annotation_types'] = Annotation.ANNOTATION_TYPES
        return context


class AnnotationView(View):
    def get(self, request, task_id):
        task = get_object_or_404(AnnotationTask, id=task_id)
        return render(request, 'annotation/annotate.html', {
            'task': task,
            'annotation_types': Annotation.ANNOTATION_TYPES
        })

    def post(self, request, task_id):
        # try:
        with transaction.atomic():
            # Parse JSON data from request body
            data = json.loads(request.body)
            print(data)
            # Extract task
            task = get_object_or_404(AnnotationTask, id=task_id)

            # Extract annotation details
            annotation_type = data.get('annotation_type')
            annotation_name = data.get("annotations").get('name')
            annotation_objects = data.get('annotations').get('data', [])
            classifications = data.get('classification', [])

            # Save annotation
            annotation = Annotation.objects.create(
                task=task,
                name=annotation_name,
                annotation_type=annotation_type,
                data=annotation_objects  # Store the raw data for further processing if needed
            )

            # Save classifications
            for classification in classifications:
                Classification.objects.create(
                    annotation=annotation,
                    name=classification['name'],
                    classification_type=classification['type'],
                    value=classification['value']
                )

            # Convert annotation to Python annotation format
            python_annotation = self._convert_to_python_annotation(annotation)

            # Upload annotations to Labelbox
            self._upload_annotations_to_labelbox(task.global_key, [python_annotation], task.project.lb_uid)

            # Trigger ExportService after annotation task upload
            export_service = ExportService()
            export_service.export_annotations(task.project.lb_uid)

            # update task object as annotated
            task.mark_as_annotated()

            return JsonResponse(
                {"message": "Annotation task created and export triggered successfully."},
                status=201,
            )

    def _convert_to_python_annotation(self, annotation):
        """
        Convert a Django Annotation object to the Labelbox Python annotation format.
        """
        classifications = [
            lb_types.ClassificationAnnotation(
                name=cls.name,
                value=lb_types.Text(answer=cls.value) if cls.classification_type == "text" else None
            )
            for cls in annotation.classifications.all()
        ]

        if annotation.annotation_type == "bounding_box":
            bbox_data = annotation.data
            print(bbox_data)
            return lb_types.ObjectAnnotation(
                name=annotation.name,
                value=lb_types.Rectangle(
                    start=lb_types.Point(x=bbox_data[0].get('left'), y=bbox_data[0].get('top')),
                    end=lb_types.Point(x=bbox_data[0].get('left') + bbox_data[0].get('width'),
                                       y=bbox_data[0].get('top') + bbox_data[0].get('height'))
                ),
                classifications=classifications
            )
        elif annotation.annotation_type == "polygon":
            points = [lb_types.Point(x=pt['x'], y=pt['y']) for pt in annotation.data]
            return lb_types.ObjectAnnotation(
                name=annotation.name,
                value=lb_types.Polygon(points=points),
                classifications=classifications
            )
        elif annotation.annotation_type == "point":
            point_data = annotation.data[0]
            return lb_types.ObjectAnnotation(
                name=annotation.name,
                value=lb_types.Point(x=point_data.get('x'), y=point_data.get('y')),
                classifications=classifications
            )
        else:
            raise ValueError(f"Unsupported annotation type: {annotation.annotation_type}")

    def _upload_annotations_to_labelbox(self, global_key, annotations, project_id):
        """
        Upload the converted annotations to Labelbox.
        """
        labelbox_service = LabelboxService()  # Assuming LabelboxService handles API calls

        label = lb_types.Label(
            data={"global_key": global_key},
            annotations=annotations
        )
        # ontology = labelbox_service.get_ontology(project_id)
        # print(ontology)
        # project = labelbox_service.client.get_project("cm4y9lxj10b3m07y97ma33952")
        # project = labelbox_service.client.get_project(project_id)
        # data_rows = list(project.datasets().data_rows())
        # data_row_keys = [row.global_key for row in data_rows]
        # print("Existing Data Row Keys:", data_row_keys)
        # upload_job = lb.MALPredictionImport.create_from_objects(
        #     client=labelbox_service.client,
        #     project_id=project_id,
        #     name=f"mal_annotation_job_{str(uuid.uuid4())}",
        #     predictions=[label]
        # )
        # Upload label for this data row in project
        # Before upload
        # if not labelbox_service.check_dataRow_exists(global_key, project_id):
        #     raise Exception(f"DataRow with global_key {global_key} does not exist in project id {project_id}")
        # print('lebel', label)
        # keys = labelbox_service.get_existing_data_row_keys(project_id)
        # print(keys)
        # Then upload
        upload_job = lb.MALPredictionImport.create_from_objects(
            client=labelbox_service.client,
            project_id=project_id,
            name="mal_job" + str(uuid.uuid4()),
            predictions=[label]
        )

        upload_job.wait_till_done()

        if upload_job.errors:
            raise Exception(f"Labelbox upload errors: {upload_job.errors}")
