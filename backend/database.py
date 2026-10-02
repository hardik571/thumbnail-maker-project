from sqlmodel import SQLModel,create_engine,Session
from config import DATABASE_URL

engine = create_engine(DATABASE_URL,echo=False,connect_args={"check_same_thread":False})
# create engine add the connection from database like poora raasta setup krna

def create_tables():#ye ek bar me hee chalta hai
    SQLModel.metadata.create_all(engine) #in it .it make table take data from meta data = job aur thumbnail aur engine ke through dbms tak data pahucha dega


def get_session():
    with Session(engine) as session:
        yield session  #session = ek tarah ka darwaza jisse hum data ko andar bahar le ja sakte hai
        #