"""
    PyHSS GSUP Update Location Request Controller
    Copyright (C) 2025  Lennart Rosam <hello@takuto.de>

    SPDX-License-Identifier: AGPL-3.0-or-later

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
from typing import List, Dict
from pydantic import BaseModel


class SubscriberUpdatedEvent(BaseModel):
    imsi: str
    msisdn: str
    apns: List[Dict[str, str]]
    disabled: bool