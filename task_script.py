import os
import django
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import Client
from core.models import Assessment, ExamSubmission, ExamNode, Paper, Qualification

User = get_user_model()

assessment = Assessment.objects.filter(paper_type='randomized', paper_link__isnull=False).order_by('-id').first()
if not assessment:
    print('No suitable assessment found.')
else:
    print(f'Found Assessment: ID={assessment.id}, EISA_ID={assessment.eisa_id}')
    qualification = assessment.qualification
    if not qualification and assessment.paper_link:
        qualification = assessment.paper_link.qualification
    users_to_create = [
        {'email': 'learner.demo@example.com', 'pwd': 'DemoLearner123!', 'role': 'learner', 'stu_num': 'STU-DEMO-001'},
        {'email': 'marker.demo@example.com', 'pwd': 'DemoMarker123!', 'role': 'assessor_marker', 'stu_num': None},
        {'email': 'internal.mod.demo@example.com', 'pwd': 'DemoInternal123!', 'role': 'internal_mod', 'stu_num': None},
        {'email': 'external.mod.demo@example.com', 'pwd': 'DemoExternal123!', 'role': 'external_mod', 'stu_num': None},
    ]
    for u_data in users_to_create:
        user, created = User.objects.update_or_create(email=u_data['email'], defaults={'is_active': True, 'role': u_data['role'], 'student_number': u_data['stu_num'], 'qualification': qualification})
        user.set_password(u_data['pwd'])
        user.save()
        print(f"User {u_data['email']} {'created' if created else 'updated'}.")
    assessment.status = 'Released to students'
    assessment.save()
    print('Assessment status set to Released to students.')
    learner = User.objects.get(email='learner.demo@example.com')
    deleted_count, _ = ExamSubmission.objects.filter(learner=learner, assessment=assessment).delete()
    print(f'Deleted {deleted_count} existing submissions.')
    nodes = ExamNode.objects.filter(paper=assessment.paper_link)
    post_data = {f'answer_node_{node.id}': 'Random Answer' for node in nodes}
    client = Client()
    client.force_login(learner)
    url = f'/submit_exam/{assessment.id}/'
    from django.urls import reverse
    try:
        url = reverse('submit_exam', args=[assessment.id])
    except:
        try:
            url = reverse('core:submit_exam', args=[assessment.id])
        except:
            pass
    print(f'Attempting POST to {url}')
    response = client.post(url, post_data)
    print(f'Response status: {response.status_code}')
    submission = ExamSubmission.objects.filter(learner=learner, assessment=assessment).last()
    print('\n--- REPORT ---')
    print(f'Assessment ID: {assessment.id}')
    print(f'EISA ID: {assessment.eisa_id}')
    print(f'Paper Name: {assessment.paper_link.title if assessment.paper_link else "N/A"}')
    print(f'Submission Created: {"Yes" if submission else "No"}')
    if submission:
        print(f'Submission ID: {submission.id}')
        pdf_path = submission.pdf_file.path if submission.pdf_file else 'No PDF file'
        print(f'Saved PDF Path: {pdf_path}')
    print('\nCredentials:')
    for u in users_to_create:
        print(f"{u['email']} / {u['pwd']} / {u['role']}")
