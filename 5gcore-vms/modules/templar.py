from typing import Dict, Any, List
from pathlib import Path

from jinja2 import FileSystemLoader, Environment

from configs import MVM_IP


class Templar:

    def __init__(self, template_dir: str) -> None:
        template_loader = FileSystemLoader(searchpath=template_dir)
        self.env = Environment(loader=template_loader)

    def render(self, src: str, **jinja_vars) -> Dict[str, Any]:
        template = self.env.get_template(src)
        generated = template.render(**jinja_vars)
        return generated

    @staticmethod
    def save(generated: str, dst: str, mkparents=False) -> None:
        if mkparents:
            Path(dst).parent.mkdir(parents=True, exist_ok=True)

        with open(dst, 'w+') as out_fd:
            out_fd.write(generated)


class CloudTemplar(Templar):
    PACKAGES = [
        'python3',
        'python3-pip',
        'python3-setuptools',
        'python3-wheel',
        'ninja-build',
        'build-essential',
        'flex',
        'bison',
        'git',
        'libsctp-dev',
        'libgnutls28-dev',
        'libgcrypt-dev',
        'libssl-dev',
        'libidn11-dev',
        'libmongoc-dev',
        'libtalloc-dev',
        'libbson-dev',
        'libyaml-dev',
        'libnghttp2-dev',
        'libmicrohttpd-dev',
        'libcurl4-gnutls-dev',
        'libnghttp2-dev',
        'libtins-dev',
        'meson'
    ]

    CPLANE_PACKAGES = [
        'mongodb'
    ]

    MVM_PACKAGES = [
        'nfs-kernel-server',
    ]

    MOUNT_NFS = [
        'mkdir -p /mnt/nfs_shared',
        f'mount {MVM_IP}:/mnt/nfs_shared /mnt/nfs_shared'
    ]

    BUILD_5GCORE = [
        'git clone https://github.com/open5gs/open5gs',
        'cd open5gs',
        'git checkout v2.4.4',
        './misc/netconf.sh',
        'meson build --prefix="${PWD}/install"',
        'ninja -C build',
        'cd build; ninja install; cd ..',
    ]

    POST_BUILD = [
        'cd /open5gs/',
        'ln -s ${PWD}/build/subprojects/freeDiameter/extensions/dict_dcca_3gpp/dict_dcca_3gpp.fdx '
            '${PWD}/build/subprojects/freeDiameter/extensions/dict_dcca_3gpp.fdx',
        'cp install/bin/open5gs-* /usr/bin/',
        'chmod -R 755 /open5gs/'
    ]

    def __init__(self,
                 template_dir: str,
                 ssh_key_path: str = str(Path('keys', 'hyper_id_rsa.pub')),
                 user_data_fn: str = 'user-data.yaml.j2',
                 network_data_fn: str = 'network-data.yaml.j2'
            ) -> None:
        super().__init__(template_dir)
        self.ssh_key_path = ssh_key_path
        self.user_data_fn = user_data_fn
        self.network_data_fn = network_data_fn

    def generate_cplane_node(self, **config):
        user_data_vars, network_data_vars = self._generate_common_config(**config)
        user_data_vars['packages'] += self.CPLANE_PACKAGES
        user_data_vars['runcmd'] = self.BUILD_5GCORE + self.POST_BUILD

        user_data = self.render(self.user_data_fn, **user_data_vars)
        network_data = self.render(self.network_data_fn, **network_data_vars)
        return {
            'user_data': user_data,
            'network_data': network_data
        }

    def generate_mvm_config(self, **config):
        user_data_vars, network_data_vars = self._generate_common_config(**config)

        user_data_vars['packages'] = self.PACKAGES + self.MVM_PACKAGES
        runcmd_nfs = [
            'mkdir /mnt/nfs_shared',
            'chown -R nobody:nogroup /mnt/nfs_shared',
            'chmod 777 /mnt/nfs_shared',
            'echo "/mnt/nfs_shared 192.168.122.0/24(rw,sync,no_subtree_check)" >> /etc/exports',
            'sudo exportfs -a',
            'sudo systemctl restart nfs-kernel-server',
        ]

        runcmd_build_binaries = [
            'cd /mnt/nfs_shared',
            'git clone https://github.com/open5gs/open5gs',
            'cd open5gs',
            'git checkout v2.3.6',
            './misc/netconf.sh',
            'meson build --prefix="/home/ops/open5gs/install"',
            'ninja -C build',
            'cd build; ninja install; cd ..'
            'chmod -R 777 /mnt/nfs_shared/open5gs/build',
            'chmod 777 /mnt/nfs_shared/open5gs/',
            'ln -s /mnt/nfs_shared/open5gs/build/subprojects/freeDiameter/extensions/dict_dcca_3gpp/dict_dcca_3gpp.fdx '
            '/mnt/nfs_shared/open5gs/build/subprojects/freeDiameter/extensions/dict_dcca_3gpp.fdx',
        ]
        user_data_vars['runcmd'] = runcmd_nfs + runcmd_build_binaries

        user_data = self.render(self.user_data_fn, **user_data_vars)
        network_data = self.render(self.network_data_fn, **network_data_vars)
        return {
            'user_data': user_data,
            'network_data': network_data
        }

    def _generate_common_config(self, **config):
        with open(self.ssh_key_path, 'r') as key_fd:
            key = key_fd.read()

        user_data_vars = {
            'hostname': config['name'],
            'keys': [key],
            'packages': self.PACKAGES
        }

        network_data_vars = {
            'interfaces': [
                {
                    'name': 'eth01',
                    'mac': config['mac'],
                    'addresses': [config['ip']],
                    'gateway4': '192.168.122.1',
                    'dns_servers': '8.8.8.8',
                }
            ]
        }
        return user_data_vars, network_data_vars