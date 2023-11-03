import os
import sys
import csv
import json
import sqlite3
import pickle
from pprint import pprint

debug = False

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

transport = RequestsHTTPTransport(
    url="https://api.courses.21-learning.com/v1/graphql",
    headers={"Authorization": f"Bearer {jwt}"},
    verify=True,
    retries=3,
)

client = Client(transport=transport, fetch_schema_from_transport=True)


def get_grade(answer, filename):
    div_id = answer["div_id"]
    sid = answer["sid"]
    question_type = answer["question_type"]
    htmlsrc = answer["htmlsrc"]
    

    text = answer["answer"]
    text = text.strip().lower()
    if debug: print("text:", text)


    if question_type in ["shortanswer"]:
        answers_to_grade = [text]

    elif question_type in ["fitb"]:
        answers_to_grade = [
            x.strip()
            .lower()
            .replace("'", "")
            .replace(" ", "")
            .replace('"', "")
            .replace(",", ".")
            .replace("-", "")
            for x in json.loads(text)
        ]
        answers_to_grade = [(i + 1, ans) for i, ans in enumerate(answers_to_grade)]
    elif question_type == "mchoice":
        nb_options = htmlsrc.count('<li data-component="answer"')
        answers_to_grade = text.split(',')
        answers_to_grade = [(i, str(i) in answers_to_grade) for i in range(nb_options)]
        if debug: print("graded", answers_to_grade)
        #answers_to_grade = [(i + 1, ans) for i, ans in enumerate(answers_to_grade)]
    else:
        if debug: print(f"Pas de correction pour la question {div_id} de type {question_type}")
        answers_to_grade = []
        return 
        

    score = 0
    comments = []

    # print(f"grading {answers_to_grade}")

    for a_to_grade in answers_to_grade:
        key = (div_id, a_to_grade)

        grades = {}

        try:
            with open(filename, "rb") as f:
                grades = pickle.load(f)
        except:
            pass

        if key in grades:
            grade, comment = grades[key]
            score += grade
        else:
            print(f"{div_id} / {sid}: Réponse: {a_to_grade}")
            while True:
                try:
                    grade = float(input("Note: "))
                    comment = input("Commentaire: ")
                    comments.append(comment)
                    grades[key] = (grade, comment)
                    with open(filename, "wb") as f:
                        pickle.dump(grades, f)
                    score += grade
                    break
                except KeyboardInterrupt:
                    return
                except Exception as e:
                    print(f"Erreur de saisie: {str(e)}")

    return max(0, score), " / ".join(comments)


def remove_all_key(div_id, filename):
    with open(filename, "rb") as f:
        grades = pickle.load(f)

    keys_to_remove = [(id, key) for (id, key) in grades if id == div_id]

    for id, key in keys_to_remove:
        del grades[(id, key)]

    with open(filename, "wb") as f:
        pickle.dump(grades, f)


def question_type(question_src: str) -> str:
    return question_src[2:].strip().split("::")[0]


def get_questions(assignment_name: str = None, q_type: str = None) -> list[str]:
    query = gql(
        """
        query questions($filter: all_questions_view_bool_exp) {
        all_questions_view(
            where: $filter,
            distinct_on: sorting_priority,
            order_by: {sorting_priority: asc}) {
            div_id
        }
    }
    """
    )

    result = client.execute(
        query,
        variable_values={
            "filter": {
                "assignment_name": {"_eq": assignment_name} if assignment_name else {},
                "question_type": {"_eq": q_type} if q_type else {},
            }
        },
    )

    return [q["div_id"] for q in result["all_questions_view"]]


def get_answers(div_id: str):
    query = gql(
        """
        query questions($div_id: String!) {
            all_questions_view(where: {div_id: {_eq: $div_id}}, distinct_on: [div_id, sid]) {
                sid
                div_id
                timestamp
                question_type
                course_name
                answer
                htmlsrc
            }
        }
    """
    )

    result = client.execute(query, variable_values={"div_id": div_id})

    return result["all_questions_view"]


def grade_answer(answer: dict, filename="grade-db.pickle") -> float:
    sid = answer["sid"]
    course_name = answer["course_name"]
    div_id = answer["div_id"]

    score, comment = get_grade(answer, filename)
    # print(answer["answer"], "=>", score)
    sql = f"""INSERT INTO question_grades (sid, course_name, div_id, score) VALUES ('{sid}', '{course_name}', '{div_id}', {score})
                ON CONFLICT (sid, course_name, div_id) DO UPDATE SET score = {score}, comment = '{comment.replace("'", "''")}';
    """
    print(sql)
    return score, comment


# remove_all_key('exa-4-c7c064f4-question-06', 'grade-db.pickle')


question_ids = get_questions("Examen 5.B")


for question_id in question_ids[:]:
    answers = get_answers(question_id)
    # print(f"Évaluation de la question {question_id}")
    for a in answers[:]:
        grade, comment = grade_answer(a)

# print(question_ids)