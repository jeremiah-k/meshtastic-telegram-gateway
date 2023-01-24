# -*- coding: utf-8 -*-
""" SQLite database module """


import logging
import time
#
from datetime import datetime, timedelta
from typing import (
    AnyStr,
)
#
from pony.orm import db_session, desc, Database, Optional, PrimaryKey, Required, Set, set_sql_debug
#
from mtg.log import conditional_log
# Actually RichConnectio is used. This import avoids circular dependency
from mtg.connection.meshtastic import MeshtasticConnection

# has to be global variable ;-(
DB = Database()

def sql_debug():
    """
    sql_debug - wrapper to enable debugging
    """
    set_sql_debug(True)

class MeshtasticNodeRecord(DB.Entity):  # pylint:disable=too-few-public-methods
    """
    MeshtasticNodeRecord: node record representation in DB
    """
    nodeId = PrimaryKey(str)
    nodeName = Required(str)
    lastHeard = Required(datetime)
    hwModel = Required(str)
    locations = Set(lambda: MeshtasticLocationRecord)
    messages = Set(lambda: MeshtasticMessageRecord)


class MeshtasticLocationRecord(DB.Entity):  # pylint:disable=too-few-public-methods
    """
    MeshtasticLocationRecord: location record representation in DB
    """
    datetime = Required(datetime)
    altitude = Required(float)
    batteryLevel = Required(float)
    latitude = Required(float)
    longitude = Required(float)
    rxSnr = Required(float)
    node = Optional(MeshtasticNodeRecord)


class MeshtasticMessageRecord(DB.Entity):  # pylint:disable=too-few-public-methods
    """
    MeshtasticMessageRecord: message record representation in DB
    """
    datetime = Required(datetime)
    message = Required(str)
    node = Optional(MeshtasticNodeRecord)


class MeshtasticFilterRecord(DB.Entity):
    """
    MeshtasticFilterRecord: filter representation in DB
    """
    # meshtastic, telegram, etc...
    connection = Required(str)
    item = Required(str)
    reason = Required(str)
    active = Required(bool)


class MeshtasticDB:
    """
    Meshtastic events database
    """

    def __init__(self, db_file: AnyStr, logger: logging.Logger):
        self.connection = None
        self.logger = logger
        DB.bind(provider='sqlite', filename=db_file, create_db=True)
        DB.generate_mapping(create_tables=True)

    def set_meshtastic(self, connection):
        self.connection = connection

    @db_session
    def get_node_record(self, node_id: AnyStr) -> MeshtasticNodeRecord:
        """
        Retrieve node record from DB

        :param node_id:
        :return:
        """
        node_record = MeshtasticNodeRecord.select(lambda n: n.nodeId == node_id).first()
        node_info = self.connection.node_info(node_id)
        last_heard = datetime.fromtimestamp(node_info.get('lastHeard', 0))
        node_name = node_info.get('user', {}).get('longName', '')
        hw_model = node_info.get('user', {}).get('hwModel', '')
        if not node_record:
            if node_name and hw_model:
                conditional_log(f'creating new record... {node_info}', self.logger, True)
                # create new record
                node_record = MeshtasticNodeRecord(
                    nodeId=node_id,
                    nodeName=node_name,
                    lastHeard=last_heard,
                    hwModel=hw_model,
                )
                return False, node_record
        conditional_log(f'using found record... {node_record}, {node_info}', self.logger, True)
        # Update lastHeard and return record
        node_record.lastHeard = last_heard  # pylint:disable=invalid-name
        return True, node_record

    @staticmethod
    @db_session
    def get_stats(node_id: AnyStr) -> AnyStr:
        """
        Get node stats

        :param node_id:
        :return:
        """
        node_record = MeshtasticNodeRecord.select(lambda n: n.nodeId == node_id).first()
        return f"Locations: {len(node_record.locations)}. Messages: {len(node_record.messages)}"

    @db_session
    def store_message(self, packet: dict) -> None:
        """
        Store Meshtastic message in DB

        :param packet:
        :return:
        """
        from_id = packet.get("fromId")
        _, node_record = self.get_node_record(from_id)
        decoded = packet.get('decoded')
        message = decoded.get('text', '')
        # Save meshtastic message
        MeshtasticMessageRecord(
            datetime=datetime.fromtimestamp(time.time()),
            message=message,
            node=node_record,
        )

    @db_session
    def store_location(self, packet: dict) -> None:
        """
        Store Meshtastic location in DB

        :param packet:
        :return:
        """
        from_id = packet.get("fromId")
        if not from_id:
            return
        _, node_record = self.get_node_record(from_id)
        # Save location
        position = packet.get('decoded', {}).get('position', {})
        # add location to DB
        MeshtasticLocationRecord(
            datetime=datetime.fromtimestamp(time.time()),
            altitude=position.get('altitude', 0),
            batteryLevel=position.get('batteryLevel', 100),
            latitude=position.get('latitude', 0),
            longitude=position.get('longitude', 0),
            rxSnr=packet.get('rxSnr', 0),
            node=node_record,
        )

    @db_session
    def get_last_coordinates(self, node_id: str):
        """
        get_last_coordinates - get last known node coordinates
        """
        node_record = MeshtasticNodeRecord.select(lambda n: n.nodeId == node_id).first()
        if not node_record:
            raise RuntimeError(f'node {node_id} not found')
        record = MeshtasticLocationRecord.select(lambda n: n.node == node_record)
        location_record = record.order_by(desc(MeshtasticLocationRecord.datetime)).first()
        if not location_record:
            raise RuntimeError(f'node {node_id} has no stored locations')
        self.logger.debug(location_record)
        return location_record.latitude, location_record.longitude

    @staticmethod
    @db_session
    def get_node_track(node_name, tail=3600):
        """
        get_node_track - return list of waypoints for building node track
        """
        data = []
        if node_name.startswith('!'):
            node_record = MeshtasticNodeRecord.select(lambda n: n.nodeId == node_name).first()
        else:
            node_record = MeshtasticNodeRecord.select(lambda n: n.nodeName == node_name).first()
        if not node_record:
            return data
        # pylint:disable=unnecessary-lambda-assignment
        cnd = lambda n: n.node == node_record and n.datetime >= datetime.now() - timedelta(seconds=tail)
        record = MeshtasticLocationRecord.select(cnd)
        location_record = record.order_by(desc(MeshtasticLocationRecord.datetime))
        for l_r in location_record:
            data.append({"lat": l_r.latitude, "lng": l_r.longitude})
        return data
