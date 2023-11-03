import os
import csv
import sqlite3
import pickle
from pprint import pprint

'''
jwt = "eyJhbGciOiAiSFM1MTIiLCAidHlwIjogIkpXVCJ9.eyJobWFjX2tleSI6ICIwNzQ1MGU5Ni1jOGQ1LTQyODMtODc5Mi02ZjdjMzliMDQ3ZWEiLCAidXNlcl9ncm91cHMiOiB7IjEiOiAiaW5zdHJ1Y3RvciJ9LCAidXNlciI6IHsiaWQiOiAxNTZ9LCAiaWF0IjogMTY4NzI4OTk0Ni4wLCAiZXhwIjogMTcxODgyNTk0Ni4wLCAiaHR0cHM6Ly8yMS1sZWFybmluZy5jb20vand0L2NsYWltcyI6IHsieC1oYXN1cmEtYWxsb3dlZC1yb2xlcyI6IFsic3R1ZGVudCIsICJ0ZWFjaGVyIl0sICJ4LWhhc3VyYS1kZWZhdWx0LXJvbGUiOiAidGVhY2hlciIsICJ4LWhhc3VyYS1vcmctaWQiOiAiMSIsICJ4LWhhc3VyYS11c2VyLWlkIjogIjE1NiJ9fQ.2x-c7qJm0JWv-By9UgkHYPy8p5x5GYDEx1U88Mf6y4uoWohpOQwSTC87Ir38uUUNetiVuFG-JfJoYXx--cEDlg"

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

transport = RequestsHTTPTransport(
    url="https://api.courses.21-learning.com/v1/graphql",
    headers={'Authorization': f'Bearer {jwt}'},
    verify=True,
    retries=3,
)

client = Client(transport=transport, fetch_schema_from_transport=True)

query = gql(
    """
    query {
  courses {
    course_name
  }
}
"""
)

result = client.execute(query)
print(result)
'''

'''
Requête SQL pour tout aspirer et avoir dans un fichier CSV

SELECT u.course_name, C.ID, 
	C.ACID as "div_id",
	C.SID,
	C.TIMESTAMP,
	regexp_replace(C.CODE, E'[\\n\\r\\u2028]+', ' ', 'g' ) as "code",
	C.CODE as "original_code"
FROM CODE C
INNER JOIN
	(SELECT ACID,
			SID,
			MAX(TIMESTAMP) AS "timestamp"
		FROM CODE
		WHERE ACID LIKE 'exadb-1-requete-%'
		GROUP BY ACID,
			SID) T ON C.ACID = T.ACID
	AND C.SID = T.SID
	AND C.TIMESTAMP = T.TIMESTAMP
inner join auth_user u ON u.username = C.sid
order by "div_id", course_name, sid


'''


def set_grade(sid, course_name, div_id, score, comment=None):
    ...

def open_db(db):
    con = sqlite3.connect(db)
    cur = con.cursor()
    return cur

def show_grades(points, total):
    for sid in sorted(points.keys()):
        p = points[sid]
        print(f"Note de {sid}: {round(p / total * 5 + 1, 1)}")

def grade(filename, db, pickle_file = 'grades.p'):
    
    try:
        grades = pickle.load( open( pickle_file, "rb" ) )
    except:
        grades = {}

    #pprint(grades, indent=2, sort_dicts=True)
    print(grades)
    
    points = {}
    
    con = sqlite3.connect(db)
    cur = con.cursor()
    
    with open(filename, newline="") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=",", quotechar='"')
        for row in reader:
            
            sid = row['sid']
            course_name = row['course_name']
            div_id = row['div_id']
            timestamp = row['timestamp']
            score = row['score']
            comment = row['comment']
            code = row['code']
            
            try:
                res = cur.execute(code)
                rows = tuple(res.fetchall())
                fields = tuple(column[0] for column in cur.description)
                if (div_id, fields, rows) in grades:
                    score, comment = grades[(div_id, fields, rows)]
                else:
                    score = float(input(f"Note pour la requête ({div_id} / {sid})\n\t{code}\n\navec headers {list(fields)}\n\nNote : "))
                    comment = input("Commentaire: ")
                    grades[(div_id, fields, rows)] = (score, comment)
                    pickle.dump( grades, open( pickle_file, "wb" ) )
                    
            except Exception as e:
                if (div_id, str(e)) in grades:
                    score, comment = grades[(div_id, str(e))]
                else:
                    score = float(input(f"{div_id} / {sid}: Erreur pour SQL: {str(e)}=\n\n\t{code}\n\nNote: "))
                    comment = input("Commentaire: ")
                    grades[(div_id, str(e))] = (score, comment)
                pickle.dump( grades, open( pickle_file, "wb" ) )
                
                
                
                
            
            
            try:
                score = float(score)
                if sid in points:
                    points[sid] += score
                else:
                    points[sid] = score
                query = f"""
                    INSERT INTO question_grades (sid, course_name, div_id, score) VALUES ('{sid}', '{course_name}', '{div_id}', {score})
                        ON CONFLICT (sid, course_name, div_id) DO UPDATE SET score = {score}, comment = '{comment.replace("'", "''")}';
                """
                # print(f"updating score of student {sid} to {score}")
                print(query)

            except ValueError as e:
                pass
            
    con.close()
    
    
    


grade("resultats.csv", os.path.join('dbs', 'ecole.db'), 'grades.p')
