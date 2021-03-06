import requests
from bs4 import BeautifulSoup
from util import normalize_str
import json
import uuid
from os import path, makedirs
import hashlib
from typing import List, Optional
from activity import Activity
from collections import defaultdict
from datetime import datetime


class Member:
    """
    Class representing a single member of the parliament
    """

    def __init__(
        self,
        first_name: str,
        last_name: str,
        party: str,
        province: str,
        language: str,
        url: Optional[str],
        alternative_names: Optional[List[str]],
        gender: str,
        date_of_birth: datetime,
        photo_url: Optional[str],
    ):
        """Class representing a single member of the parliament

        Args:
            first_name (str): First name of the member
            last_name (str): Last name of the member
            party (str): Party affiliation of the member
            province (str): Province the member ran in
            language (str): Language of the member
            url (str, optional): URL to the wikipedia page of the member. Defaults to None.
            alternative_names (List[str], optional): Alternative spellings of the member name. This deals with typos and short variants of names.
            gender (str): The gender of the member
            date_of_birth (datetime): The date of birth of the member
            photo_url (str, optional): The url of a photo of the member
        """
        self.first_name = first_name
        self.last_name = last_name
        self.party = party
        self.province = province
        self.language = language
        self.alternative_names = alternative_names
        self.replaces = []
        self.activities = []
        self.url = url
        self.date_of_birth = date_of_birth
        self.gender = gender
        self.photo_url = photo_url
        sha_1 = hashlib.sha1()
        sha_1.update(self.first_name.encode('utf-8') + self.last_name.encode('utf-8') +
                     self.province.encode('utf-8'))
        # TODO: add defensive mechanism that can detect a collision, even though it is extremely unlikely
        self.uuid = sha_1.hexdigest()[:10]  # Should be sufficiently random

    @staticmethod
    def from_json(json_entry):
        """Constructs a member from its static json representation.
        
        Args:
            json_entry: The static json representation
        """

        import dateparser
        date_of_birth = dateparser.parse(json_entry['date_of_birth'])
        return Member(
            json_entry['first_name'],
            json_entry['last_name'],
            json_entry['party'],
            json_entry['province'],
            json_entry['language'],
            json_entry['wiki'],
            json_entry.get('alternative_names'),
            json_entry['gender'],
            date_of_birth,
            json_entry.get('photo_url')
        )

    def uri(self):
        return f'members/{self.uuid}.json'

    def dump_json(self, base_path: str, base_URI="/"):
        base_path = path.join(base_path, "members")
        base_URI_members = f'{base_URI}members/'
        resource_name = f'{self.uuid}.json'
        makedirs(base_path, exist_ok=True)

        with open(path.join(base_path, resource_name), 'w+') as fp:
            replaces = list(map(lambda replacement: {
                            'member': f'{base_URI_members}{replacement["member"]}.json', 'dates': replacement['dates']}, self.replaces))
            activity_dict = defaultdict(lambda: defaultdict(list))
            for activity in self.activities:
                activity_dict[str(activity.date.year)][str(
                    activity.date.isoformat())].append(activity.dict(base_URI))
            activities_dir = path.join(base_path, str(self.uuid))
            makedirs(activities_dir, exist_ok=True)

            activity_uris = {}

            for year in activity_dict:
                with open(path.join(activities_dir, f'{year}.json'), 'w+') as afp:
                    json.dump(activity_dict[year], afp)
                activity_uris[year] = f'{base_URI_members}{self.uuid}/{year}.json'

            json.dump({'id': str(self.uuid), 'first_name': self.first_name, 'last_name': self.last_name, 'gender': self.gender, 'date_of_birth': self.date_of_birth.isoformat(
            ), 'language': self.language, 'province': self.province, 'party': self.party, 'wiki': self.url, 'replaces': replaces, 'activities': activity_uris, 'photo_url': self.photo_url}, fp, ensure_ascii=False)

        return f'{base_URI_members}{resource_name}'

    def __repr__(self):
        return "Member(\"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\")" % (self.first_name, self.last_name, self.party, self.province, self.language, self.url)

    def __str__(self):
        return "%s, %s" % (self.first_name, self.last_name)

    def normalized_name(self):
        return normalize_str(("%s %s" % (self.first_name, self.last_name)).lower()).decode()

    def post_activity(self, activity: Activity):
        self.activities.append(activity)

    def has_name(self, query: str):
        """Compare the query string with the "{last_name} {first_name}" combination of
        this member, ignoring any diactritical characters. Alternative names are also possible for
        the member, this is sometimes necessary.

        Args:
            query (str): Name as seen in the meeting notes of the parliament.

        Returns:
            bool: Is this the name of this member
        """
        query = normalize_str(query)
        name = normalize_str("%s %s" % (self.last_name, self.first_name))
        # Fallback for alternative names
        if self.alternative_names:
            for n in self.alternative_names:
                if query == normalize_str(n):
                    return True
        # Fallback for meetings in session 52, < 90
        if query == normalize_str(self.last_name):
            return True
        return query == name or query == normalize_str(f'{self.first_name} {self.last_name}')

    def set_replaces(self, replaces: List[any]):
        """Set which members are replaces when by this member.

        Args:
            replaces (list): All the timespans a member was replaced
        """
        self.replaces = replaces
