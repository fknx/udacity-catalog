from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine

Base = declarative_base()

class Category(Base):

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable = False)
    items = relationship("Item", backref="category")

    @property
    def serialize(self):
        return {
            'id' : self.id,
            'name' : self.name,
            'items' : [item.serialize for item in self.items]
        }

    def serializeToXml(self, content):
        content.append("<Category>")
        content.append("<ID>%s</ID>" % self.id)
        content.append("<Name>%s</Name>" % self.name)

        if self.items:
            content.append("<Items>")

            for item in self.items:
                item.serializeToXml(content)

            content.append("</Items>")
        else:
            content.append("<Items/>")

        content.append("</Category>")

class Item(Base):

    __tablename__ = "items"

    id = Column(Integer, primary_key = True)
    name = Column(String(255), nullable = False)
    description = Column(Text, nullable = True)
    creation_date = Column(DateTime, nullable = False)

    category_id = Column(Integer, ForeignKey("categories.id"))

    @property
    def serialize(self):
        return {
            'id' : self.id,
            'name' : self.name,
            'description' : self.description,
            'creation_date' : self.creation_date
        }

    def serializeToXml(self, content):
        content.append("<Item>")
        content.append("<ID>%s</ID>" % self.id)
        content.append("<Name>%s</Name>" % self.name)

        if self.description:
            content.append("<Description>%s</Description>" % self.description)
        else:
            content.append("<Description/>")

        content.append("<CreationDate>%s</CreationDate>" % self.creation_date.isoformat())

        content.append("</Item>")

if __name__ == '__main__':
    engine = create_engine('sqlite:///itemcatalog.db')
    Base.metadata.create_all(engine)

    DBSession = sessionmaker(bind=engine)
    session = DBSession()

    session.add(Category(name="Soccer"))
    session.add(Category(name="Basketball"))
    session.add(Category(name="Baseball"))
    session.add(Category(name="Frisbee"))
    session.add(Category(name="Snowboarding"))
    session.add(Category(name="Rock Climbing"))
    session.add(Category(name="Football"))
    session.add(Category(name="Skating"))
    session.add(Category(name="Hockey"))

    session.commit()
