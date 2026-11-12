"""Modele ait olmayan, veritabanından gelen güvenilir kaynak atıfları."""


def source_reference(record: dict) -> dict:
    reference = {
        'source_record_id': record['issueid'],
        'record_type': record.get('record_type', 'ticket'),
        'domain': record.get('domain', 'general_it'),
        'title': record.get('title', ''),
        'source_name': record.get('source_name', ''),
        'source_url': record.get('source_url', ''),
    }
    for key in ('source_author', 'license', 'license_url', 'execution_tested', 'answer_url', 'question_author', 'answer_author', 'question_license', 'answer_license',
                'question_license_url', 'answer_license_url', 'official_verification_status', 'official_sources', 'transformation'):
        if key in record:
            reference[key] = record[key]
    return reference
