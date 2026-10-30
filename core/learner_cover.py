import json
from django.utils import timezone


FIELDS = ('Student name and surname', 'Student number', 'Identity number', 'Assessment centre',
          'Accreditation number', 'Qualification', 'SAQA ID', 'NQF level', 'Credits',
          'Paper number', 'Date of EISA', 'Duration', 'Total marks')


def cover_defaults(user, assessment):
    centre = user.assessment_centre
    qualification = assessment.qualification
    info = (assessment.paper_link.structure_json or {}).get('randomization', {}) if assessment.paper_link_id and isinstance(assessment.paper_link.structure_json, dict) else {}
    number = str(info.get('set_number') or ('1' if assessment.module_number.isalpha() else ''))
    letter = ''.join(c for c in assessment.module_number if c.isalpha())
    paper_number = number + letter if number else assessment.module_number
    result = dict(zip(FIELDS, [user.get_full_name() or user.username, user.student_number or '',
        user.identity_number, centre.name if centre else '', centre.accreditation_number if centre else '',
        qualification.name if qualification else '', assessment.saqa_id or getattr(qualification, 'saqa_id', '') or '',
        str(getattr(qualification, 'nqf_level', '') or ''), str(getattr(qualification, 'credits', '') or ''),
        paper_number, timezone.localdate().isoformat(), '',
        str(assessment.paper_link.total_marks if assessment.paper_link_id else '')]))
    if assessment.paper_link_id:
        from bs4 import BeautifulSoup
        aliases = {'NQFLEVEL': 'NQF level', 'CREDITS': 'Credits', 'DURATION': 'Duration', 'TOTALMARKS': 'Total marks'}
        def normalise(value):
            return ''.join(c for c in value.upper() if c.isalnum())
        def scan(value):
            if isinstance(value, str):
                if '<table' in value.lower():
                    soup = BeautifulSoup(value, 'html.parser')
                    for row in soup.find_all('tr'):
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            label = aliases.get(normalise(cells[0].get_text(' ', strip=True)))
                            if label:
                                result[label] = cells[1].get_text(' ', strip=True)[:300]
                else:
                    try:
                        scan(json.loads(value))
                    except (ValueError, TypeError):
                        pass
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, list) and len(item) >= 2:
                        label = aliases.get(normalise(str(item[0])))
                        if label:
                            result[label] = str(item[1])[:300]
                    scan(item)
            elif isinstance(value, dict):
                for item in value.values():
                    scan(item)
        for node in assessment.paper_link.nodes.filter(node_type='cover_page'):
            scan(node.content)
    metadata = assessment.paper_link.structure_json if assessment.paper_link_id and isinstance(assessment.paper_link.structure_json, dict) else {}
    minutes = round(float(metadata.get('duration_hours', 3)) * 60)
    hours, minutes = divmod(minutes, 60)
    result['Duration'] = f"{hours} hour{'s' if hours != 1 else ''}" + (f" {minutes} minutes" if minutes else '') if hours else f"{minutes} minutes"
    return result


def read_cover(post, user, assessment):
    result = cover_defaults(user, assessment)
    for index, label in enumerate(FIELDS):
        value = post.get(f'cover_{index}')
        if value is not None and label != 'Duration':
            result[label] = value.strip()[:300]
    # Student number is an account identifier, not an editable identity override.
    result['Student number'] = user.student_number or ''
    return result


def read_writing_notes(post):
    result = {}
    for key, value in post.items():
        if not key.startswith('notes_'):
            continue
        try:
            blocks = json.loads(value)
        except (ValueError, TypeError):
            continue
        if not isinstance(blocks, list):
            continue
        text = '\n'.join(str(block.get('text', ''))[:10000] for block in blocks[:100] if isinstance(block, dict)).strip()
        if text:
            result[key[:100]] = text[:50000]
    return result
