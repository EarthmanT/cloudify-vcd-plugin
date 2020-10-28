# Copyright (c) 2020 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .base import VCloudResource


class VCloudDisk(VCloudResource):

    def __init__(self,
                 disk_name,
                 connection=None,
                 vdc_name=None,
                 kwargs=None):

        self.disk_name = disk_name
        self.kwargs = kwargs or {}
        self._disk = None
        if 'name' in self.kwargs:
            del self.kwargs['name']

        super().__init__(connection, vdc_name)
        self.vapp_name = self._vapp_name
        self._vapp = None

    @property
    def disk(self):
        if not self._disk:
            self._disk = self.get_disk(self.disk_name)
        return self._disk

    def get_disk(self, disk_name):
        return self.vdc.get_disk(disk_name)

    def create(self):
        return self.vdc.create_disk(self.disk_name, **self.kwargs)

    def delete(self):
        return self.vdc.delete_disk(self.vapp_name)

    def update(self, **kwargs):
        kwargs = kwargs or self.kwargs
        if 'name' in kwargs:
            del kwargs['name']
        identifier = kwargs.get('disk_id', self.disk_name)
        return self.vdc.update_disk(identifier, **kwargs)
