"""
This is a class to setup the data connections for a
item catalog with categories web application
"""
from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
from passlib.apps import custom_app_context as app_context
import random
import string
from itsdangerous import(
        TimedJSONWebSignatureSerializer as Serializer,
        BadSignature,
        SignatureExpired
    )

BASE = declarative_base()

# This secret_key will be used to both encrypt and decrypt
secret_key = (
        ''.join(random.choice(
                string.ascii_uppercase + string.digits) for x in xrange(32)
                )
    )


class User(BASE):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    username = Column(String(32), index=True, unique=True)
    password_hash = Column(String(120))
    email = Column(String(250), index=True, unique=True)
    # active = Column(Integer, default=0)

    def hash_password(self, password):
        self.password_hash = app_context.encrypt(password)

    def verify_password(self, password):
        return app_context.verify(password, self.password_hash)

    def generate_auth_token(self, expiration=600):
        """
        Use itsdangerous.TimedJSONWebSignatureSerializer
        to encrypt a token, and the secret key created global
        in the class.

        Parameters:
            self

            [optional]
            expiraexpiration: integer, seconds until expires

        Returns: encrypted token, containing id of the user
        """
        s = Serializer(secret_key, expires_in=expiration)
        return s.dumps({'id': self.id})

    @property
    def serialize(self):
        """Return the object fields as JSON like format"""
        return {
            'name': self.username,
            'id': self.id,
            'email': self.email
        }

    @staticmethod
    def verify_auth_token(token):
        """
        Purpose: Decrypt a token and check for the user id.
                 Exceptions are thrown for expired tokens,
                 and for BadSignatures. If these exceptions
                 are found, "None" is returned

        Params: A token created with Serializer

        Returns: a user_id if successfully decrypted
                 from the token
        """

        s = Serializer(secret_key)
        try:
            data = s.loads(token)
        except SignatureExpired:
            print("Expired token")
            return None
        except BadSignature:
            print("Bad token: {0}".format(BadSignature.message))
            return None

        print("if bad token,this shouldn't print")
        user_id = data['id']
        return user_id


class Category(BASE):
    """
    Define category class
    Extends a constant of an instance of declarative_base()
    """

    __tablename__ = 'category'

    name = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)
    items = relationship("Item", cascade="delete, delete-orphan")

    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    user = relationship(User)

    @property
    def serialize(self):
        """Return the object fields as JSON like format"""
        return {
            'name': self.name,
            'id': self.id,
            'owner_username': self.user.username
        }


class Item(BASE):
    """
    Define category class
    Extends a constant of an instance of declarative_base()
    """

    __tablename__ = 'item'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    description = Column(String(250))
    price = Column(String(8))

    cat_id = Column(Integer, ForeignKey('category.id'), nullable=False)
    category = relationship(Category)

    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    user = relationship(User)

    @property
    def serialize(self):
        """Return the object fields as JSON like format"""
        return {
            'name': self.name,
            'description': self.description,
            'id': self.id,
            'price': self.price,
            'category': self.category.name,
            'category_id': self.cat_id,
            'owner_username': self.user.username
        }

ENGINE = create_engine('postgresql+psycopg2://catalog:F0rW3b5!@localhost/catalog')

BASE.metadata.create_all(ENGINE)
