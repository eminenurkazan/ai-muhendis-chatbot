"""Explicitly reviewed official guides: one complete, bounded procedure per chunk."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit
from psycopg.types.json import Jsonb
from database.connection import connect
from database.import_expertise import digest
import ticket_vektor_arama as vectors


def load_record(path):
    row = json.loads(Path(path).read_text(encoding='utf-8'))
    required = ('source_record_id', 'source_name', 'source_url', 'source_version', 'source_author',
                'license', 'license_url', 'title', 'problem', 'solution', 'limitations',
                'product_version_environment', 'resolution', 'official_context', 'transformation')
    if any(not isinstance(row.get(k), str) or not row[k].strip() for k in required):
        raise ValueError('Rehberin kaynak, koşul veya içerik alanı eksik.')
    if (urlsplit(row['source_url']).scheme != 'https'
            or urlsplit(row['source_url']).hostname not in {'learn.microsoft.com', 'docs.oracle.com'}
            or row.get('domain') not in {'windows_server', 'oracle_db'}
            or row.get('record_type') != 'documentation' or row.get('solution_scope') != 'procedure'
            or row.get('resolution_confirmed', 'missing') is not None
            or row.get('official_verification_status') != 'official_source_scoped'
            or row.get('execution_tested') is not False):
        raise ValueError('İlk rehber aktarımı için kaynak/kapsam doğrulaması geçersiz.')
    # Komut zorunlu değildir (bazı rehberler yalnız çözüm adımlarıdır); varsa rehberde bire bir bulunmalıdır.
    commands = row.get('commands')
    if not isinstance(commands, list) or any(not isinstance(c, str) or not c.strip() or c not in row['solution'] for c in commands):
        raise ValueError('Komutlar tam rehberde bulunmalı.')
    if len(embedding_text(row)) > 12000:
        raise ValueError('Rehber çok uzun: ön koşulları koruyan ayrı alt rehberler hazırlayın.')
    return row


def embedding_text(row):
    return '\n'.join(f'{k}: {row[k]}' for k in ('title', 'domain', 'problem',
        'product_version_environment', 'solution', 'resolution', 'limitations'))


def load_vector(row, cache):
    data = json.loads(Path(cache).read_text(encoding='utf-8'))
    if (data.get('record_hash') != digest(row) or data.get('model') != vectors.MODEL
            or data.get('text_hash') != digest(embedding_text(row))):
        raise ValueError('Embedding önbelleği rehberle eşleşmiyor.')
    return vectors.normalized_vector(data['vector'])


def embed(row, cache):
    if Path(cache).exists():
        load_vector(row, cache)
        return
    import rag_ticket_pilotu as rag
    if not rag.cloudflare_credentials_path().exists():
        raise ValueError('Kayıtlı Cloudflare erişimi bulunamadı.')
    account, token, _ = rag.cloudflare_credentials()
    try:
        vector = vectors.cloud_embeddings(account, token, [embedding_text(row)])[0]
    finally:
        del token
    with Path(cache).open('x', encoding='utf-8') as handle:
        json.dump({'record_hash': digest(row), 'text_hash': digest(embedding_text(row)),
                   'model': vectors.MODEL, 'vector': vector}, handle, ensure_ascii=False)


def snapshot(connection, excluded):
    return connection.execute('''SELECT count(*),md5(coalesce(string_agg(to_jsonb(r)::text,'|' ORDER BY r.id),''))
        FROM knowledge_records r WHERE source_record_id<>%s''', (excluded,)).fetchone(), connection.execute('''
        SELECT count(*),md5(coalesce(string_agg(to_jsonb(c)::text,'|' ORDER BY c.id),''))
        FROM knowledge_chunks c JOIN knowledge_records r ON r.id=c.record_id WHERE r.source_record_id<>%s''', (excluded,)).fetchone()


def import_record(row, cache):
    vector = load_vector(row, cache)
    with connect() as connection:
        connection.execute('SELECT pg_advisory_xact_lock(191198006)')
        before = snapshot(connection, row['source_record_id'])
        existing = connection.execute('SELECT content_hash FROM knowledge_records WHERE source_record_id=%s', (row['source_record_id'],)).fetchall()
        if existing:
            if existing != [(digest(row),)]:
                raise ValueError('Kaynak kimliği farklı içerikle kayıtlı; üzerine yazılmadı.')
            return {'added': 0, 'already_present': 1}
        sid = connection.execute('''INSERT INTO knowledge_sources (name,source_type,source_url,license,source_version)
            VALUES (%s,'official_documentation',%s,%s,%s) ON CONFLICT (name,source_version)
            DO UPDATE SET name=EXCLUDED.name RETURNING id''', (row['source_name'], row['source_url'], row['license'], row['source_version'])).fetchone()[0]
        metadata = dict(row)
        metadata['official_sources'] = [{'title': row['title'], 'url': row['source_url']}]
        text = embedding_text(row)
        rid = connection.execute('''INSERT INTO knowledge_records
            (source_id,source_record_id,record_type,domain,title,cleaned_text,problem,solution,
             resolution,resolution_confirmed,solution_scope,limitations,metadata,review_status,index_status,content_hash)
            VALUES (%s,%s,'documentation',%s,%s,%s,%s,%s,%s,NULL,'procedure',%s,%s,'approved','ready',%s) RETURNING id''',
            (sid,row['source_record_id'],row['domain'],row['title'],text,row['problem'],row['solution'],row['resolution'],row['limitations'],Jsonb(metadata),digest(row))).fetchone()[0]
        connection.execute('''INSERT INTO knowledge_chunks (record_id,chunk_index,chunk_text,embedding,embedding_model,record_content_hash)
            VALUES (%s,0,%s,%s,%s,%s)''', (rid,text,vector,vectors.MODEL,digest(row)))
        if before != snapshot(connection, row['source_record_id']):
            raise ValueError('Önceki kayıtlar değişti; aktarım geri alındı.')
    return {'added': 1, 'previous_records_unchanged': before[0][0], 'previous_chunks_unchanged': before[1][0]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check','embed','import','verify'])
    parser.add_argument('--record', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    args = parser.parse_args()
    row = load_record(args.record)
    if args.action == 'check':
        result = {'checked': row['source_record_id']}
    elif args.action == 'embed':
        embed(row, args.cache)
        result = {'embedded': 1, 'dimensions': vectors.DIMENSION}
    elif args.action == 'import':
        result = import_record(row, args.cache)
    else:
        from database.search import search_chunks
        hits = search_chunks(load_vector(row, args.cache), embedding_model=vectors.MODEL, domains=('general_it',row['domain']))
        found = next((r for _,r in hits if r['issueid'] == row['source_record_id']), None)
        if not found or found['solution'] != row['solution'] or found['record_type'] != 'documentation':
            raise ValueError('Rehber arama/içerik kontrolü başarısız.')
        result = {'verified': row['source_record_id'], 'self_vector_top3': True, 'execution_tested': False}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
