"""Idempotent synthetic content for development demonstrations only."""
from __future__ import annotations
from datetime import date,timedelta
from .db import connection

CATEGORIES={
 'Electrónica':['Sistemas digitales','Circuitos y medición','Microcontroladores','Señales electrónicas','Diseño embebido'],
 'Ingeniería eléctrica':['Máquinas eléctricas','Protecciones eléctricas','Sistemas de potencia','Energías renovables','Instalaciones eléctricas'],
 'Control automático':['Control moderno','Instrumentación industrial','Sistemas dinámicos','Automatización','Control de procesos'],
 'Computación':['Algoritmos','Bases de datos','Arquitectura de software','Redes de computadores','Sistemas operativos'],
 'Inteligencia artificial':['Aprendizaje automático','Visión computacional','Procesamiento de lenguaje','Ética de la IA','Redes neuronales'],
 'Matemática':['Cálculo aplicado','Álgebra lineal','Probabilidad','Métodos numéricos','Ecuaciones diferenciales'],
 'Física':['Mecánica universitaria','Electromagnetismo','Óptica','Termodinámica','Física moderna'],
 'Ingeniería mecánica':['Diseño de máquinas','Mecánica de fluidos','Manufactura','Materiales','Transferencia de calor'],
 'Ingeniería civil':['Estructuras','Geotecnia','Hidráulica','Construcción sostenible','Topografía'],
 'Medicina':['Anatomía clínica','Salud pública','Fisiología','Bioética','Epidemiología'],
 'Educación':['Didáctica universitaria','Evaluación del aprendizaje','Tecnología educativa','Psicología educativa','Investigación pedagógica'],
 'Ciencias sociales':['Sociología andina','Economía regional','Historia del Perú','Antropología','Políticas públicas'],
}

def seed():
    with connection() as conn:
        conn.execute("""INSERT INTO library_branches(code,name,address,source_url,verified)
          VALUES ('BIB-DEMO','Biblioteca piloto (DEMO)','Ubicación sintética','https://example.invalid/demo',false)
          ON CONFLICT(code) DO NOTHING""")
        number=0
        for category,titles in CATEGORIES.items():
            for index,title in enumerate(titles,1):
                number+=1
                external_id=f'DEMO-LIB-{number:03d}'
                conn.execute("""INSERT INTO library_books(external_id,title,authors,subject,branch_code,catalog_url,
                  availability,verified,source_label,description,total_copies,available_copies,demo_record)
                  VALUES (%s,%s,%s,%s,'BIB-DEMO','https://example.invalid/demo','not_verified',false,'demonstration',%s,4,4,true)
                  ON CONFLICT(external_id) DO UPDATE SET title=excluded.title,authors=excluded.authors,subject=excluded.subject,
                    description=excluded.description,total_copies=GREATEST(library_books.total_copies,excluded.total_copies),
                    available_copies=CASE WHEN library_books.demo_record THEN library_books.available_copies ELSE excluded.available_copies END,
                    demo_record=true,source_label='demonstration'""",
                    (external_id,f'{title}: edición demostrativa',[f'Autor ficticio {category} {index}'],category,
                     'Registro sintético creado para probar búsqueda y reservas. No pertenece al catálogo oficial.'))
        conn.execute("""INSERT INTO dining_locations(code,name,address,source_url,verified)
          VALUES ('COM-DEMO','Comedor piloto (DEMO)','Ubicación sintética','https://example.invalid/demo',false)
          ON CONFLICT(code) DO NOTHING""")
        meals=('Desayuno andino demostrativo','Almuerzo vegetariano demostrativo','Cena ligera demostrativa')
        kinds=('breakfast','lunch','dinner')
        for offset in range(7):
            day=date.today()+timedelta(days=offset)
            for kind,description in zip(kinds,meals):
                conn.execute("""INSERT INTO dining_menus(location_code,service_date,meal_type,description,source_url,verified,quota,demo_record)
                  VALUES ('COM-DEMO',%s,%s,%s,'https://example.invalid/demo',false,40,true)
                  ON CONFLICT(location_code,service_date,meal_type) DO UPDATE SET description=excluded.description,
                    quota=excluded.quota,demo_record=true""",(day,kind,description))
        organizer=conn.execute("SELECT id FROM community_users WHERE id='demo-estudiante'").fetchone()
        if organizer:
            groups=(
              ('electronica','Ingeniería Electrónica'),('robotica','Robótica'),('programacion','Programación'),
              ('investigacion','Investigación'),('deportes','Deportes'),('emprendimiento','Emprendimiento'),
              ('cultura','Cultura'),('vida-universitaria','Vida universitaria'))
            for slug,name in groups:
                group=conn.execute("""INSERT INTO community_groups(slug,name,description,visibility,created_by)
                  VALUES (%s,%s,%s,'public','demo-estudiante') ON CONFLICT(slug) DO UPDATE SET name=excluded.name
                  RETURNING id""",(slug,name,f'Grupo ficticio de {name} para la demostración del MVP.')).fetchone()
                conn.execute("""INSERT INTO community_memberships(group_id,user_id,role)
                  VALUES (%s,'demo-estudiante','owner') ON CONFLICT DO NOTHING""",(group['id'],))
                conn.execute("""INSERT INTO community_posts(author_id,group_id,body,category,demo_key)
                  VALUES ('demo-estudiante',%s,%s,'general',%s)
                  ON CONFLICT(demo_key) WHERE demo_key IS NOT NULL DO UPDATE SET body=excluded.body,group_id=excluded.group_id""",
                  (group['id'],f'Bienvenidas y bienvenidos a {name}. Esta publicación y sus participantes son ficticios.',f'DEMO-POST-{slug}'))
            event_names=('Robótica abierta','Feria de investigación','Taller de programación','Encuentro deportivo','Círculo de lectura','Emprendimiento regional')
            for index in range(24):
                starts=date.today()+timedelta(days=index+1)
                conn.execute("""INSERT INTO community_events(organizer_id,title,description,location_name,starts_at,ends_at,capacity,demo_record,demo_key)
                  VALUES ('demo-estudiante',%s,%s,%s,%s::date+interval '15 hours',%s::date+interval '17 hours',60,true,%s)
                  ON CONFLICT(demo_key) WHERE demo_key IS NOT NULL DO UPDATE SET title=excluded.title,
                    description=excluded.description,location_name=excluded.location_name,starts_at=excluded.starts_at,
                    ends_at=excluded.ends_at,capacity=excluded.capacity,demo_record=true""",
                    (f'{event_names[index%len(event_names)]} · DEMO',
                     'Actividad sintética para probar inscripciones. No constituye una convocatoria oficial.',
                     f'Espacio demostrativo {index%5+1}',starts,starts,f'DEMO-EVENT-{index+1:02d}'))
    return {'books':sum(len(items) for items in CATEGORIES.values()),'menu_days':7,'events':24,'groups':8}

if __name__=='__main__': print(seed())
