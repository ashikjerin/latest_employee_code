import os
from flask import Flask,request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from ariadne import load_schema_from_path, make_executable_schema, \
    graphql_sync, snake_case_fallback_resolvers, ObjectType,convert_kwargs_to_snake_case
from ariadne.constants import PLAYGROUND_HTML


# Defining database
app = Flask(__name__)
print("Our current working directory is == >",os.getcwd())   # current working directory
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.getcwd()}/employee.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False    # disables track modification
db = SQLAlchemy(app)


@app.route('/')
def hello():
    return 'Hello!'

# Defining DataType for Employee table
class Employee(db.Model):
    __tablename__ = 'Employee'
    emp_id = db.Column(db.Integer, primary_key=True)
    emp_name = db.Column(db.String)
    dep_id = db.Column(db.Integer, db.ForeignKey('Department.dep_id'))
    hire_date = db.Column(db.Date)
    job_name = db.Column(db.String)
    salary = db.Column(db.Integer)
# Defining Table
    def table1(self):
        return {
            "emp_id": self.emp_id,
            "dep_id": self.dep_id,
            "emp_name": self.emp_name,
            "hire_date": str(self.hire_date.strftime('%d-%m-%Y')),
            "job_name": self.job_name,
            "salary": self.salary
        }

# Defining DataType for Department table
class Department(db.Model):
    __tablename__ = 'Department'
    dep_id = db.Column(db.Integer, primary_key=True)
    dep_name = db.Column(db.String)
    location = db.Column(db.String)

# Defining Table
    def table2(self):
        return {
            "dep_id": self.dep_id,
            "dep_name": self.dep_name,
            "location": self.location
        }

# Query
def resolve_employees(obj, info):
    try:
        employees = [i.table1() for i in Employee.query.all()]
        departments = [i.table2() for i in Department.query.all()]
        payload = {
            "success": True,
            "employees": employees,
            "departments": departments
        }
    except Exception as error:
        payload = {
            "success": False,
            "errors": [str(error)]
        }
    return payload



@convert_kwargs_to_snake_case
def resolve_emp(obj, info, employee_id):
    try:
        employee = Employee.query.get(employee_id)
        payload = {
            "success": True,
            "employee": employee.table1()
        }

    except AttributeError:  # todo not found
        payload = {
            "success": False,
            "errors": [f"Employee item matching id {employee_id} not found"]
        }

    return payload

#Mutation
@convert_kwargs_to_snake_case
def resolve_create_employee(obj, info, emp_name,hire_date, job_name, salary, dep_name, location):
    try:
        db.create_all()
        hire_date = datetime.strptime(hire_date, '%d-%m-%Y').date()
        employee = Employee(emp_name=emp_name, hire_date=hire_date, job_name=job_name, salary=salary)
        department = Department(dep_name=dep_name, location=location)
        db.session.add(employee)
        db.session.add(department)
        db.session.commit()
        payload = {
            "success": True,
            "employee": employee.table1(),
            "department": department.table2()
        }

    except ValueError:  # date format errors
        payload = {
            "success": False,
            "errors": ["Incorrect payload"]
        }

    return payload
#Delete
@convert_kwargs_to_snake_case
def resolve_delete_employee(obj, info, emp_id):
    try:
        employee = Employee.query.get(emp_id)
        db.session.delete(employee)
        db.session.commit()
        payload = {"success": True}

    except AttributeError:
        payload = {
            "success": False,
            "errors": [f"Employee matching id {emp_id} not found"]
        }

    return payload

#Update
@convert_kwargs_to_snake_case
def resolve_update_hire_date(obj, info, emp_id, new_date):
    try:
        employee = Employee.query.get(emp_id)
        # if employee:
        employee.hire_date = datetime.strptime(new_date, '%d-%m-%Y').date()
        db.session.add(employee)
        db.session.commit()
        payload = {
            "success": True,
            "employee": employee.table1()
        }

    except ValueError:  # date format errors
        payload = {
            "success": False,
            "errors": ["Incorrect date format provided. Date should be in "
                       "the format dd-mm-yyyy"]
        }
    except AttributeError:  # Employee not found
        payload = {
            "success": False,
            "errors": [f"Employee matching id {emp_id} not found"]
        }
    return payload

query = ObjectType("Query")


query.set_field("employees", resolve_employees)
query.set_field("employee", resolve_emp)

mutation = ObjectType("Mutation")
mutation.set_field("createEmployee", resolve_create_employee)
mutation.set_field("deleteEmployee", resolve_delete_employee)
mutation.set_field("updateHireDate", resolve_update_hire_date)


type_defs = load_schema_from_path("employee1.graphql")
schema = make_executable_schema(
    type_defs, query, mutation, snake_case_fallback_resolvers
)

@app.route("/graphql", methods=["GET"])
def graphql_playground():
    return PLAYGROUND_HTML, 200


@app.route("/graphql", methods=["POST"])
def graphql_server():
    data = request.get_json()
    # print("data==>",data)
    success, result = graphql_sync(
        schema,
        data,
        context_value=request,
        debug=app.debug
    )
    status_code = 200 if success else 400

    return jsonify(result), status_code

if __name__=="__main__":
    app.run(debug=True)

