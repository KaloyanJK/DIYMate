from django.shortcuts import render, redirect, get_object_or_404
from .models import Project
from .forms import ProjectForm
from django.contrib.auth.decorators import login_required

# CREATE
@login_required
def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.user = request.user
            project.save()
            return redirect('project_list')
    else:
        form = ProjectForm()

    return render(request, 'projects/create_project.html', {'form': form})


# READ (LIST)
@login_required
def project_list(request):
    projects = Project.objects.filter(user=request.user)
    return render(request, 'projects/project_list.html', {'projects': projects})


# READ (DETAIL)
@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, id=pk, user=request.user)
    return render(request, 'projects/project_detail.html', {'project': project})


# UPDATE
@login_required
def edit_project(request, pk):
    project = get_object_or_404(Project, id=pk, user=request.user)

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            return redirect('project_list')
    else:
        form = ProjectForm(instance=project)

    return render(request, 'projects/edit_project.html', {'form': form})


# DELETE
@login_required
def delete_project(request, pk):
    project = get_object_or_404(Project, id=pk, user=request.user)

    if request.method == 'POST':
        project.delete()
        return redirect('project_list')

    return render(request, 'projects/delete_project.html', {'project': project})