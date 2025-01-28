from enum import Enum
from flask import Flask, logging, request, jsonify 
from flask_sqlalchemy import SQLAlchemy 
from flask_cors import CORS 
from datetime import datetime, timedelta
from sqlalchemy import Enum as SQLAlchemyEnum 
import logging

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app, resources={r"/*": {"origins": "*"}})
db = SQLAlchemy(app)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class LoanType(Enum):
    TYPE_1 = 1  # 10 days
    TYPE_2 = 2  # 5 days
    TYPE_3 = 3  # 2 days

    @classmethod
    def get_max_loan_days(cls, loan_type):
        if loan_type == cls.TYPE_1:
            return 10
        elif loan_type == cls.TYPE_2:
            return 5
        elif loan_type == cls.TYPE_3:
            return 2
        return None

class Book(db.Model):
    __tablename__ = 'books'

    book_id = db.Column(db.Integer, primary_key=True)
    book_name = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    year_published = db.Column(db.Integer, nullable=False)
    loan_type = db.Column(SQLAlchemyEnum(LoanType), nullable=False)
    active = db.Column(db.Boolean, default=True)
    loans = db.relationship('Loan', back_populates='book') 

    def __repr__(self):
        return f'<Book {self.book_name}, {self.author}>'


class Customer(db.Model):
    __tablename__ = 'customers'

    customer_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    phone_number = db.Column(db.String(10), nullable=False, default="Not specified")
    active = db.Column(db.Boolean, default=True)
    # Relationship to Loans (one-to-many)
    loans = db.relationship('Loan', back_populates='customer')

    def __repr__(self):
        return f'<Customer {self.name}>'


class Loan(db.Model):
    __tablename__ = 'loans'

    loan_id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.book_id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False)
    loan_date = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.Date, nullable=True)
    active = db.Column(db.Boolean, default=True)

    # Relationships
    book = db.relationship('Book', back_populates='loans')
    customer = db.relationship('Customer', back_populates='loans')

    def __repr__(self):
        return f'<Loan {self.loan_id}>'


with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return jsonify({"home": "server is alive"})


@app.route('/get_customers', methods=['GET'])
def display_customers():  # active customers
    customers = Customer.query.filter_by(active=True).all()
    return jsonify([
        {
            'customer_id': customer.customer_id,
            'name': customer.name,
            'city': customer.city,
            'age': customer.age,
            'phone number': customer.phone_number
        }
        for customer in customers
    ])


@app.route('/add_customer', methods=['POST'])
def add_customer():
    data = request.get_json()
    required_fields = ['name', 'phone_number']  # Fields that are mandatory

    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"'{field}' is required."}), 400
    # check existing customer by name and phone number.
    existing_customer = Customer.query.filter_by(
        name=data['name'], phone_number=data['phone_number']).first()

    if existing_customer:
        return jsonify({"message": "This Customer already exists!"}), 400

    logger.info(f"Adding new customer: {data['name']}")
    add_customer_to_list(data)

    return jsonify({"message": "Customer added successfully!"}), 201

def add_customer_to_list(data):
    new_customer = Customer(
        name=data['name'],
        city=data.get('city'),
        age=data.get('age'),
        phone_number =data.get('phone_number')
    )

    db.session.add(new_customer)
    db.session.commit()
    logger.info(f"Customer {new_customer.name} added to the database.")


def testAddCustomer():
    customer1= Customer(name='David Cohen',city='holon', age=30, phone_number='025456325')
    customer2= Customer(name='Maayan Levi', city='haifa', age=28, phone_number='0555555555')
    customer3= Customer(name='Itai Goldberg',city='telaviv',age= 35,phone_number='0222222222')
    customer4= Customer(name='Nitay', city='tel aviv', age=17, phone_number='0512345678')
    customer5= Customer(name='Tamar Ben-David', city='netanya', age=40, phone_number='089562314')
    customer6 = Customer(name='Yossi Cohen', city='jerusalem', age=45, phone_number='0523456789')
    customer7 = Customer(name='Roni Levy', city='beersheba', age=22, phone_number='0501234567')
    customer8 = Customer(name='Maya Shimon', city='eilat', age=33, phone_number='0539876543')


    db.session.add_all([customer1, customer2, customer3, customer4, customer5, customer6,customer7,customer8])
    db.session.commit()

    return "Customers added successfully!"


@app.route('/remove_customer/<int:customer_id>', methods=['PUT'])
def deactive_customer(customer_id):
    customer = Customer.query.get(customer_id)

    if not customer:
        return jsonify({'error': 'Customer not found'}), 404

    # Update the customer's active status to False (inactive)
    customer.active = False
    db.session.commit()  # Commit the changes to the database

    logger.info(f"Customer {customer_id} deactivated successfully.")
    return jsonify({
        'message': f'Customer {customer_id} has been deactivated successfully',
        'customer_id': customer.customer_id,
        'name': customer.name,
        'active': customer.active
    })


@app.route('/add_book', methods=['POST'])
def add_book():
    data = request.get_json()
    
    if 'loan_type' not in data:
        return jsonify({"error": "loan_type is required."}), 400
    try:
        loan_type_value = LoanType(data['loan_type'])
    except ValueError:
        return jsonify({"error": "Invalid loan type. Please use 1, 2, or 3."}), 400
    
    logger.info(f"Adding new book: {data['book_name']}")
    return create_new_book(data, loan_type_value)

def create_new_book(data, loan_type_value):
    new_book = Book(
        book_name=data['book_name'],
        author=data['author'],
        year_published=data['year_published'],
        loan_type=loan_type_value.name # Days the book can be loaned (enum options)
    )
    db.session.add(new_book)
    db.session.commit()
    logger.info(f"Book {new_book.book_name} added to the database.")
    return jsonify({ 
        "message": "Book added successfully!",
        "loan_type":loan_type_value.name,
        "max_loan_days": LoanType.get_max_loan_days(loan_type_value) 
        }), 201

def testAddBook():
    book1= Book(book_name='keep trying', author='jim black', year_published=1990, loan_type="TYPE_2")
    book2 = Book(book_name='The Great Adventure', author='Sarah Green', year_published=2001, loan_type="TYPE_1")
    book3 = Book(book_name='Python Programming', author='John Smith', year_published=2015, loan_type="TYPE_3")
    book4 = Book(book_name='The Mystery of the Lost City', author='Emily Rose', year_published=2008, loan_type="TYPE_2")
    book5 = Book(book_name='Data Science for Beginners', author='Michael Johnson', year_published=2020, loan_type="TYPE_1")
    book6 = Book(book_name='The Final Countdown', author='Jessica Williams', year_published=2010, loan_type="TYPE_3")
    book7 = Book(book_name='The Art of War', author='Sun Tzu', year_published=1500, loan_type="TYPE_2")
    book8 = Book(book_name='Ocean of Secrets', author='Nina White', year_published=2018, loan_type="TYPE_1")

    db.session.add_all([book1, book2, book3, book4, book5, book6, book7, book8])
    db.session.commit()

    return "Books added successfully!"

@app.route('/get_books', methods=['GET'])
def display_all_books():  # active books
    try:
        books = Book.query.filter_by(active=True).all()
        return jsonify([
            {
                'book_id': book.book_id,
                'book_name': book.book_name,
                'author': book.author,
                'year_published': book.year_published,
                'loan_type': book.loan_type.name
            }
            for book in books
        ])
    except Exception as e:
        logger.error(f"Error retrieving books: {str(e)}")
        return jsonify({"error": "An error occurred while fetching books."}), 500


@app.route('/remove_book/<int:book_id>', methods=['PUT'])
def deactive_book(book_id):
    book = Book.query.get(book_id)

    if not book:
        return jsonify({'error': 'Book not found'}), 404

    # Update the book's active status to False (inactive)
    book.active = False
    db.session.commit()  # Commit the changes to the database

    logger.info(f"Book {book_id} deactivated successfully.")
    return jsonify({
        'message': f'Book {book_id} has been deactivated successfully',
        'book_id': book.book_id,
        'name': book.book_name,
        'active': book.active
    })


@app.route('/search_book/<string:book_name>', methods=['GET'])
def search_book_by_name(book_name):
    books = Book.query.filter(Book.book_name.ilike(f"%{book_name}%"), Book.active == True).all()
    if books:
        return jsonify([
            {
                'book_id': book.book_id,
                'name': book.book_name,
                'author': book.author,
                'year published': book.year_published,
                'loan type': book.loan_type.name
            }
            for book in books]), 200
    else:
        return jsonify({"message": "No active books found with this name."}), 404

@app.route('/loan_book', methods=['POST'])
def loan_book():
    data = request.get_json()

    # Find the book and customer by their ids
    book = Book.query.get(data['book_id'])
    customer = Customer.query.get(data['customer_id'])

    if not book or not customer:
        return jsonify({"message": "Book or Customer not found!"}), 404
    if not book.active:
        return jsonify({"message": "This book is not available!"}), 400
    
    try:
        loan_date = datetime.strptime(data['loan_date'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"message": "Invalid date format, please use YYYY-MM-DD!"}), 400    
   
    loan_type_enum = book.loan_type  
    max_loan_days = LoanType.get_max_loan_days(loan_type_enum)
    if max_loan_days is None:
        return jsonify({"message": "Invalid loan type!"}), 400

    return_date = loan_date + timedelta(days=max_loan_days)

    book.active = False

    add_new_loan(book, customer, loan_date, return_date)

    logger.info(f"Book {book.book_name} loaned to customer {customer.name}. Due date: {return_date}.")
    return jsonify({
        "message": f"Book loaned successfully! Please return the book in {max_loan_days} days.",
        "days_until_return": max_loan_days}), 201

def add_new_loan(book, customer, loan_date, return_date):
    new_loan = Loan(
        book_id=book.book_id,
        customer_id=customer.customer_id,
        loan_date=loan_date,
        return_date=return_date,
        active=True  
    )
    db.session.add(new_loan)
    try:
        db.session.commit() 
    except Exception as e:
        db.session.rollback()  # rtry again if something goes wrong
        logger.error(f"Error saving loan: {str(e)}")
        return jsonify({"message": f"Error saving loan: {str(e)}"}), 500

def testAddingloans():

    loan1 = Loan(book_id=1, customer_id=1, loan_date=datetime.strptime('2024-06-12', '%Y-%m-%d').date(), return_date=datetime.strptime('2024-06-20', '%Y-%m-%d').date())
    loan2 = Loan(book_id=2, customer_id=2, loan_date=datetime.strptime('2024-07-01', '%Y-%m-%d').date(), return_date=datetime.strptime('2024-07-05', '%Y-%m-%d').date())
    loan3 = Loan(book_id=3, customer_id=3, loan_date=datetime.strptime('2024-07-10', '%Y-%m-%d').date(), return_date=datetime.strptime('2024-07-12', '%Y-%m-%d').date())
    loan4 = Loan(book_id=4, customer_id=4, loan_date=datetime.strptime('2024-07-15', '%Y-%m-%d').date(), return_date=datetime.strptime('2024-07-18', '%Y-%m-%d').date())
    loan5 = Loan(book_id=5, customer_id=5, loan_date=datetime.strptime('2024-07-20', '%Y-%m-%d').date(), return_date=datetime.strptime('2024-07-25', '%Y-%m-%d').date())
    loan6 = Loan(book_id=6, customer_id=6, loan_date=datetime.strptime('2024-07-22', '%Y-%m-%d').date(), return_date=datetime.strptime('2024-07-25', '%Y-%m-%d').date())
    loan7 = Loan(book_id=7, customer_id=7, loan_date=datetime.strptime('2024-07-25', '%Y-%m-%d').date(), return_date=datetime.strptime('2024-07-30', '%Y-%m-%d').date())
    loan8 = Loan(book_id=8, customer_id=8, loan_date=datetime.strptime('2024-08-01', '%Y-%m-%d').date(), return_date=datetime.strptime('2024-08-05', '%Y-%m-%d').date())


    db.session.add_all([loan1, loan2, loan3, loan4, loan5, loan6, loan7, loan8])
    db.session.commit()

@app.route('/return_book', methods=['PUT'])
def return_book():
    data = request.get_json()

    book = Book.query.get(data['book_id'])
    customer = Customer.query.get(data['customer_id'])

    if not book or not customer:
        return jsonify({"message": "Book or Customer not found!"}), 404

    # Find the active loan record for this customer and book
    loan = Loan.query.filter_by(
        book_id=book.book_id, customer_id=customer.customer_id, active=True).first()

    if not loan:
        return jsonify({"message": "No active loan found for this book and customer!"}), 404

    actual_return_date = datetime.today().date()

    loan_type_enum = loan.book.loan_type  
    max_return_date = loan.loan_date + timedelta(days=LoanType.get_max_loan_days(loan_type_enum))

    # Check if the book is returned late
    if actual_return_date > max_return_date:
        overdue_days = (actual_return_date - max_return_date).days
        message = f"Book returned late by {overdue_days} day(s)."
    else:
        message = "Book returned successfully on time!"
    # Update loan with the actual return date 
    loan.return_date = actual_return_date
    loan.active = False  
    book.active = True  

    db.session.commit()

    logger.info(f"Book {book.book_name} returned by customer {customer.name} on {actual_return_date}.")
    return jsonify({
        "message": message,
        "actual_return_date": actual_return_date.strftime('%Y-%m-%d')
    }), 200

@app.route('/display_all_loans', methods=['GET'])
def display_all_loans():
    loans = Loan.query.filter_by(active=True).all()
    return jsonify([
        {
            'loan_id': loan.loan_id,
            'book_id': loan.book_id,
            'customer_id': loan.customer_id,
            'loan_date': loan.loan_date.strftime('%Y-%m-%d'),
            'return_date': loan.return_date.strftime('%Y-%m-%d') if loan.return_date else None,
            'active': loan.active
        }
        for loan in loans
    ]), 200



@app.route('/search_customer/<string:name>', methods=['GET'])
def search_customer(name):
    app.logger.info(f"Searching for active customers with name: {name}")  
    try:
        customers = Customer.query.filter_by(name=name, active=True).all()
        
        if customers:
            app.logger.info(f"Found {len(customers)} active customer(s) with name: {name}")
            return jsonify([
                {
                    'customer_id': customer.customer_id,
                    'name': customer.name,
                    'city': customer.city,
                    'age': customer.age,
                    'loans': [
                        {
                            'loan_id': loan.loan_id,
                            'book_id': loan.book_id,
                            'loan_date': loan.loan_date,
                            'return_date': loan.return_date
                        }
                        for loan in customer.loans  # customer loans
                    ]
                }
                for customer in customers
            ]), 200
        else:
            app.logger.warning(f"No active customers found with name: {name}")
            return jsonify({"message": "No active customers found with that name."}), 404

    except Exception as e:
        app.logger.error(f"Error occurred while searching for customer: {e}")
        return jsonify({"message": "An error occurred while searching for the customer."}), 500


@app.route('/late_loans', methods=['GET'])
def late_loans():
    app.logger.info("Fetching late loans...")  
    today = datetime.now().date()
    
    try:
        late_loans = db.session.query(Loan, Customer).join(Customer).filter(
            Loan.return_date != None, Loan.return_date < today, Loan.active==True).all()

        app.logger.info(f"Found {len(late_loans)} late loan(s)") 

        return jsonify([
            {
                'loan_id': loan.loan_id,
                'book_id': loan.book_id,
                'loan_date': loan.loan_date.strftime('%Y-%m-%d'),
                'return_date': loan.return_date.strftime('%Y-%m-%d'),
                'customer': {
                    'customer_id': customer.customer_id,
                    'name': customer.name,
                    'city': customer.city,
                    'age': customer.age
                }
            }
            for loan, customer in late_loans
        ]), 200
    except Exception as e:
        app.logger.error(f"Error occurred while fetching late loans: {e}")
        return jsonify({"message": "An error occurred while fetching late loans."}), 500                

    


if __name__ == '__main__':

    with app.app_context():  
        # testAddCustomer()
        # testAddBook()
        # testAddingloans()
        db.session.commit()
        app.run(debug=True)
    
