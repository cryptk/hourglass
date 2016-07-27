import aiohttp
import asyncio
from flask.ext.sqlalchemy import BaseQuery
from flask import abort
import hourglass
from hourglass.db import db
from hourglass.utils import get_filters_list


class ExtraOut(BaseQuery):

    def all_dict_out(self):
        return [x.dict_out for x in self]

    def all_dict_extra_out(self):
        return [x.dict_extra_out for x in self]

    def all_dict_out_or_404(self):
        dict_list = self.all_dict_out()
        if not dict_list:
            abort(404)
        return dict_list

    def all_dict_extra_out_or_404(self):
        dict_list = self.all_dict_extra_out()
        if not dict_list:
            abort(404)
        return dict_list


class BaseMetadata(db.Model):

    __bind_key__ = 'cache'
    __tablename__ = 'metadata'

    zone_name = db.Column(db.String(64), primary_key=True)
    entity = db.Column(db.String(64), primary_key=True)
    key = db.Column(db.String(128), primary_key=True)
    value = db.Column(db.String(512))
    updated_at = db.Column(db.DateTime, default=db.func.now(),
                           onupdate=db.func.now())

    __table_args__ = (
        db.ForeignKeyConstraint(['zone_name'], ['zones.name']),
    )

    def __init__(self, zone_name, key, entity, value):
        self.zone_name = zone_name
        self.key = key
        self.entity = entity
        self.value = value

    def __repr__(self):
        return '<%s %s: %s - %s>' % (self.__class__.__name__, self.zone_name,
                                     self.key, self.value)


class CacheBase(object):

    metadata_class = BaseMetadata
    query_class = ExtraOut
    extra = db.Column(db.Text)
    backend = db.Column(db.String(20))
    last_poll_time = db.Column(db.DateTime, default=db.func.now(),
                               onupdate=db.func.now())

    __mapper_args__ = {
        'polymorphic_on': backend,
        'polymorphic_identity': 'base'
    }

    @property
    def dict_extra_out(self):
        event_dict = self.dict_out
        event_dict['extra'] = self.extra
        return event_dict

    @classmethod
    def filter_api_response(cls, response):
        return response

    @classmethod
    def last_poll_status(cls, zone_name):
        last_run = cls.metadata_class.query.filter(
            cls.metadata_class.key == 'update_status',
            cls.metadata_class.entity == cls.__tablename__,
            cls.metadata_class.zone_name == zone_name).first()
        last_run_message = cls.metadata_class.query.filter(
            cls.metadata_class.key == 'update_message',
            cls.metadata_class.entity == cls.__tablename__,
            cls.metadata_class.zone_name == zone_name).first()
        return (last_run.updated_at, last_run.value, last_run_message.value)

    @classmethod
    def update_last_poll_status(cls, zone_name, status):
        cls.metadata_class.query.filter(
            cls.metadata_class.key == 'update_status',
            cls.metadata_class.entity == cls.__tablename__,
            cls.metadata_class.zone_name == zone_name).delete()
        return cls.metadata_class(zone_name, 'update_status',
                                  cls.__tablename__, status)

    @classmethod
    def update_last_poll_message(cls, zone_name, message):
        cls.metadata_class.query.filter(
            cls.metadata_class.key == 'update_message',
            cls.metadata_class.entity == cls.__tablename__,
            cls.metadata_class.zone_name == zone_name).delete()
        return cls.metadata_class(zone_name, 'update_message',
                                  cls.__tablename__, message)


class Client(CacheBase, db.Model):

    class ClientQuery(ExtraOut):

        def all_dict_out(self):
            clients_silences = self.outerjoin(Silence, db.and_(
                Client.zone_name == Silence.zone_name,
                Client.name == Silence.client_name,
                Silence.check_name == '')).add_entity(Silence).all()
            clients_json = []
            for client, silence in clients_silences:
                client_json = client.dict_out
                if silence:
                    client_json['silenced'] = True
                else:
                    client_json['silenced'] = False
                clients_json.append(client_json)
            return clients_json

    query_class = ClientQuery
    __bind_key__ = 'cache'
    __tablename__ = 'clients'

    zone_name = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(256), primary_key=True)
    updated_at = db.Column(db.DateTime)
    version = db.Column(db.String(256), primary_key=True)
    address = db.Column(db.String(256), primary_key=True)

    events = db.relationship('Event', backref='client', lazy='dynamic',
                             query_class=ExtraOut, primaryjoin="and_("
                             "Client.zone_name==foreign(Event.zone_name), "
                             "Client.name==foreign(Event.client_name))")

    results = db.relationship('Result', backref='client', lazy='dynamic',
                              query_class=ExtraOut, primaryjoin="and_("
                              "Client.zone_name==foreign(Result.zone_name), "
                              "Client.name==foreign(Result.client_name))")

    silences = db.relationship('Silence', backref='client', lazy='dynamic',
                               query_class=ExtraOut, primaryjoin="and_("
                               "Client.zone_name == foreign("
                               "Silence.zone_name), "
                               "Client.name == foreign(Silence.client_name))")

    __table_args__ = (
        db.ForeignKeyConstraint(['zone_name'], ['zones.name']),
    )

    def __init__(self, zone_name, extra):
        raise NotImplemented

    @property
    def status(self):
        results = self.results.all()
        if all([True if (x.status == 'ok') else False for x in results]):
            return 'ok'
        elif any([True if (x.status == 'critical') else False
                  for x in results]):
            return 'critical'
        else:
            return 'warning'

    @property
    def silenced(self):
        if self.silences.filter(Silence.check_name == '').first():
            return True
        else:
            return False

    @classmethod
    def get_dashboard_filters_list(cls, config, dashboard):
        if config['dashboards'].get(dashboard) is None:
            return ()
        zones = config['dashboards'][dashboard].get('zone')
        clients = config['dashboards'][dashboard].get('client')
        filters = ((zones, cls.zone_name),
                   (clients, cls.name))
        return get_filters_list(filters)

    @property
    def dict_out(self):
        return {
            'zone_name': self.zone_name,
            'backend': self.backend,
            'updated_at': self.updated_at,
            'version': self.version,
            'address': self.address,
            'last_poll_time': self.last_poll_time,
            'name': self.name
        }

    def __repr__(self):
        return '<%s %s/%s>' % (self.__class__.__name__, self.zone_name,
                               self.name)


class Check(CacheBase, db.Model):

    __bind_key__ = 'cache'
    __tablename__ = 'checks'

    zone_name = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(256), primary_key=True)
    occurrences_threshold = db.Column(db.BigInteger)
    interval = db.Column(db.BigInteger)
    command = db.Column(db.Text)

    results = db.relationship('Result', backref='check', lazy='dynamic',
                              query_class=ExtraOut,
                              primaryjoin="and_("
                              "Check.zone_name==foreign(Result.zone_name), "
                              "Check.name==foreign(Result.check_name))")
    events = db.relationship('Event', backref='check', lazy='dynamic',
                             query_class=ExtraOut,
                             primaryjoin="and_("
                             "Check.zone_name==foreign(Event.zone_name), "
                             "Check.name==foreign(Event.check_name))")

    __table_args__ = (
        db.ForeignKeyConstraint(['zone_name'], ['zones.name']),
    )

    def __init__(self, zone_name, extra):
        raise NotImplemented

    @classmethod
    def get_dashboard_filters_list(cls, config, dashboard):
        if config['dashboards'].get(dashboard) is None:
            return ()
        zones = config['dashboards'][dashboard].get('zone')
        checks = config['dashboards'][dashboard].get('check')
        filters = ((zones, cls.zone_name),
                   (checks, cls.name))
        return get_filters_list(filters)

    @property
    def dict_out(self):
        return {
            'zone_name': self.zone_name,
            'backend': self.backend,
            'last_poll_time': self.last_poll_time,
            'name': self.name,
            'occurrences_threshold': self.occurrences_threshold,
            'interval': self.interval,
            'command': self.command
        }

    def __repr__(self):
        return '<%s %s/%s>' % (self.__class__.__name__, self.zone_name,
                               self.name)


class Result(CacheBase, db.Model):

    class ResultQuery(ExtraOut):

        def all_dict_out(self):
            clients_silences = self.outerjoin(Silence, db.and_(
                Result.zone_name == Silence.zone_name,
                Result.client_name == Silence.client_name,
                Result.check_name == Silence.check_name)).add_entity(
                Silence).all()
            events_json = []
            for event, silence in clients_silences:
                event_json = event.dict_out
                if silence:
                    event_json['silenced'] = True
                else:
                    event_json['silenced'] = False
                events_json.append(event_json)
            return events_json

    query_class = ResultQuery
    __bind_key__ = 'cache'
    __tablename__ = 'results'

    zone_name = db.Column(db.String(64), primary_key=True)
    client_name = db.Column(db.String(256), primary_key=True)
    check_name = db.Column(db.String(256), primary_key=True)
    occurrences_threshold = db.Column(db.BigInteger)
    status = db.Column(db.String(256))
    interval = db.Column(db.BigInteger)
    command = db.Column(db.Text)
    output = db.Column(db.Text)

    __table_args__ = (
        db.ForeignKeyConstraint(['zone_name'], ['zones.name']),
        db.CheckConstraint(status.in_(
            ['ok', 'warning', 'critical', 'unknown']))
    )

    def __init__(self, zone_name, extra):
        raise NotImplemented

    @classmethod
    def get_dashboard_filters_list(cls, config, dashboard):
        if config['dashboards'].get(dashboard) is None:
            return ()
        zones = config['dashboards'][dashboard].get('zone')
        checks = config['dashboards'][dashboard].get('check')
        clients = config['dashboards'][dashboard].get('client')
        statuses = config['dashboards'][dashboard].get('status')
        filters = ((zones, cls.zone_name),
                   (checks, cls.check_name),
                   (clients, cls.client_name),
                   (statuses, cls.status))
        return get_filters_list(filters)

    @property
    def dict_out(self):
        return {
            'zone_name': self.zone_name,
            'backend': self.backend,
            'last_poll_time': self.last_poll_time,
            'client_name': self.client_name,
            'check_name': self.check_name,
            'occurrences_threshold': self.occurrences_threshold,
            'status': self.status,
            'interval': self.interval,
            'command': self.command,
            'output': self.output
        }

    def __repr__(self):
        return '<%s %s/%s/%s>' % (self.__class__.__name__, self.zone_name,
                                  self.client_name, self.check_name)


class Event(CacheBase, db.Model):

    class EventQuery(ExtraOut):

        def all_dict_out(self):
            clients_silences = self.outerjoin(Silence, db.and_(
                Event.zone_name == Silence.zone_name,
                Event.client_name == Silence.client_name,
                Event.check_name.in_(
                    [Silence.check_name, '']))).add_entity(Silence).all()
            events_json = []
            for event, silence in clients_silences:
                event_json = event.dict_out
                if silence:
                    event_json['silenced'] = True
                else:
                    event_json['silenced'] = False
                events_json.append(event_json)
            return events_json

    query_class = EventQuery
    __bind_key__ = 'cache'
    __tablename__ = 'events'

    zone_name = db.Column(db.String(64), primary_key=True)
    client_name = db.Column(db.String(256), primary_key=True)
    check_name = db.Column(db.String(256), primary_key=True)
    updated_at = db.Column(db.DateTime)
    occurrences_threshold = db.Column(db.BigInteger)
    occurrences = db.Column(db.BigInteger)
    status = db.Column(db.String(256))
    command = db.Column(db.Text)
    interval = db.Column(db.BigInteger)
    output = db.Column(db.Text)

    silences = db.relationship('Silence', backref='events', lazy='dynamic',
                               query_class=ExtraOut,
                               primaryjoin="and_("
                               "Event.zone_name==foreign(Silence.zone_name),"
                               "Event.client_name==foreign("
                               "Silence.client_name), "
                               "Event.check_name==foreign("
                               "Silence.check_name))")

    __table_args__ = (
        db.ForeignKeyConstraint(['zone_name'], ['zones.name']),
        db.CheckConstraint(status.in_(
            ['ok', 'warning', 'critical', 'unknown']))
    )

    def __init__(self, zone_name, extra):
        raise NotImplemented

    @classmethod
    def get_dashboard_filters_list(cls, config, dashboard):
        if config['dashboards'].get(dashboard) is None:
            return ()
        zones = config['dashboards'][dashboard].get('zone')
        checks = config['dashboards'][dashboard].get('check')
        clients = config['dashboards'][dashboard].get('client')
        statuses = config['dashboards'][dashboard].get('status')
        filters = ((zones, cls.zone_name),
                   (checks, cls.check_name),
                   (clients, cls.client_name),
                   (statuses, cls.status))
        return get_filters_list(filters)

    @property
    def dict_out(self):
        return {
            'backend': self.backend,
            'zone_name': self.zone_name,
            'last_poll_time': self.last_poll_time,
            'client_name': self.client_name,
            'check_name': self.check_name,
            'updated_at': self.updated_at,
            'occurrences_threshold': self.occurrences_threshold,
            'occurrences': self.occurrences,
            'status': self.status,
            'interval': self.interval,
            'command': self.command,
            'output': self.output,
        }

    def __repr__(self):
        return '<%s %s/%s/%s>' % (self.__class__.__name__, self.zone_name,
                                  self.client_name, self.check_name)


class Silence(CacheBase, db.Model):

    __bind_key__ = 'cache'
    __tablename__ = 'silences'

    zone_name = db.Column(db.String(64), primary_key=True)
    client_name = db.Column(db.String(256), primary_key=True)
    check_name = db.Column(db.String(256), nullable=True, primary_key=True,
                           default="")
    created_at = db.Column(db.DateTime)
    expire_at = db.Column(db.DateTime)
    comment = db.Column(db.Text)

    __table_args__ = (
        db.ForeignKeyConstraint(['zone_name'], ['zones.name']),
    )

    def __init__(self, zone_name, extra):
        raise NotImplemented

    @property
    def dict_out(self):
        return {
            'zone_name': self.zone_name,
            'backend': self.backend,
            'last_poll_time': self.last_poll_time,
            'client_name': self.client_name,
            'check_name': self.check_name,
            'created_at': self.created_at,
            'expire_at': self.expire_at,
            'comment': self.comment
        }

    def __repr__(self):
        return '<%s %s/%s/%s>' % (self.__class__.__name__, self.zone_name,
                                  self.client_name, self.check_name)


class Zone(CacheBase, db.Model):

    __bind_key__ = 'cache'
    __tablename__ = 'zones'

    models = [Check, Client, Event, Silence, Result]

    name = db.Column(db.String(64), primary_key=True)
    host = db.Column(db.String(64))
    path = db.Column(db.String(64))
    protocol = db.Column(db.String(64))
    port = db.Column(db.Integer())
    timeout = db.Column(db.Integer())
    username = db.Column(db.String(64))
    password = db.Column(db.String(64))
    verify_ssl = db.Column(db.Boolean())

    clients = db.relationship('Client', backref='zone', lazy='dynamic',
                              query_class=ExtraOut)
    checks = db.relationship('Check', backref='zone', lazy='dynamic',
                             query_class=ExtraOut)
    events = db.relationship('Event', backref='zone', lazy='dynamic',
                             query_class=ExtraOut)
    results = db.relationship('Result', backref='zone', lazy='dynamic',
                              query_class=ExtraOut)
    silences = db.relationship('Silence', backref='zone', lazy='dynamic',
                               query_class=ExtraOut)

    def __init__(self, name, host=None, path='/', protocol='http', port=80,
                 timeout=30, username=None, password=None, verify_ssl=True,
                 **kwargs):
        self.name = name
        self.host = host
        self.path = path
        self.protocol = protocol
        self.port = port
        self.timeout = timeout
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl

    def query_api(self, uri):
        raise NotImplementedError

    @asyncio.coroutine
    def update_objects(self, model):
        raise NotImplementedError

    def get_update_tasks(self, app):
        tasks = []
        for model in self.models:
            tasks.append(asyncio.async(self.update_objects(app, model)))
        return tasks

    @classmethod
    def get_dashboard_filters_list(cls, config, dashboard):
        if config['dashboards'].get(dashboard) is None:
            return ()
        zones = config['dashboards'][dashboard].get('zone')
        filters = ((zones, cls.name),)
        return get_filters_list(filters)

    @property
    def pollers_health(self):
        pollers = []
        overall_health = []
        for model in self.models:
            updated_at, status, message = model.last_poll_status(self.name)
            pollers.append({'name': model.__tablename__,
                            'updated_at': updated_at,
                            'status': status,
                            'message': message})
            overall_health.append(True) if status == 'ok' else \
                overall_health.append(False)
        if all(overall_health):
            overall_health = 'ok'
        elif any(overall_health):
            overall_health = 'warning'
        else:
            overall_health = 'critical'
        return overall_health, pollers

    @property
    def dict_out(self):
        overall_health, pollers = self.pollers_health
        return {
            'name': self.name,
            'backend': self.backend,
            'status': overall_health,
            'pollers': pollers
        }

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.name)


class HttpZoneMixin(object):

    @property
    def base_url(self):
        if self.path:
            url = '%s://%s:%s/%s' % (self.protocol, self.host, self.port,
                                     self.path.strip('/'))
        else:
            url = '%s://%s:%s' % (self.protocol, self.host, self.port)
        return url

    def _create_session(self):
        auth = aiohttp.BasicAuth(self.username, self.password) \
            if (self.username and self.password) else None
        conn = aiohttp.TCPConnector(verify_ssl=False) \
            if not self.verify_ssl else None
        headers = {'User-Agent': 'Hourglass/%s' % hourglass.__version__}
        return aiohttp.ClientSession(auth=auth, connector=conn,
                                     headers=headers)

    @asyncio.coroutine
    def get(self, session, url, expected_status=[200]):
        try:
            with aiohttp.Timeout(self.timeout):
                response = yield from session.get(url)
        except asyncio.TimeoutError:
            raise aiohttp.errors.ClientError('Timeout exceeded')
        if response.status not in expected_status:
            response.close()
            raise aiohttp.errors.ClientError('Unexpected response from %s, got'
                                             ' %s' % (url, response.status))
        return (yield from response.json())

    @asyncio.coroutine
    def update_objects(self, app, model):
        init_objects = []
        results = []
        url = '%s/%s' % (self.base_url, model.uri)
        try:
            with self._create_session() as session:
                app.logger.debug('Making request to %s' % url)
                response = yield from self.get(session, url)
                results = model.filter_api_response(response)
        except aiohttp.errors.ClientError as e:
            message = 'Error updating %s cache for %s: %s' % (
                model.__tablename__, self.name, e)
            app.logger.error(message)
            init_objects.append(model.update_last_poll_status(
                self.name, 'critical'))
            init_objects.append(model.update_last_poll_message(
                self.name, message))
            return init_objects
        model.query.filter(model.zone_name == self.name).delete()
        init_objects.append(model.update_last_poll_status(
            self.name, 'ok'))
        init_objects.append(model.update_last_poll_message(
            self.name, 'Success'))
        for result in results:
            init_objects.append(model(self.name, result))
        app.logger.info('Updated %s cache for %s' % (
            model.__tablename__, self.name))
        return init_objects
