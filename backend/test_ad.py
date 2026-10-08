from ldap3 import Server, Connection, ALL, SUBTREE
from ldap3.core.exceptions import LDAPBindError, LDAPException

# Configuration for your domain
AD_SERVER = 'HNL-DC.hnl.tv'
AD_DOMAIN = 'hnl.tv'
BASE_DN = 'DC=hnl,DC=tv'

# Test credentials - replace with a real AD username and password
TEST_USERNAME = 'aamish.mirza'
TEST_PASSWORD = '123456'

def test_connection():
    server = Server(AD_SERVER, get_info=ALL)
    
    try:
        # Bind using UPN format (username@domain)
        conn = Connection(
            server,
            user=f'{TEST_USERNAME}@{AD_DOMAIN}',
            password=TEST_PASSWORD,
            auto_bind=True
        )
        print('[+] Successfully bound to Active Directory.')
        
        # Search for the user to retrieve attributes
        conn.search(
            search_base=BASE_DN,
            search_filter=f'(&(objectClass=user)(sAMAccountName={TEST_USERNAME}))',
            search_scope=SUBTREE,
            attributes=['sAMAccountName', 'givenName', 'sn', 'mail', 'memberOf']
        )
        
        if conn.entries:
            entry = conn.entries[0]
            print(f'[+] Found user: {entry.sAMAccountName}')
            print(f'    Name: {entry.givenName} {entry.sn}')
            print(f'    Email: {entry.mail}')
            print(f'    Groups: {entry.memberOf}')
        else:
            print('[-] User authenticated but not found in search. Check Base DN or filter.')
        
        conn.unbind()
        return True
        
    except LDAPBindError as e:
        print(f'[-] Authentication failed: Invalid credentials.')
        return False
    except LDAPException as e:
        print(f'[-] LDAP error: {e}')
        return False

if __name__ == '__main__':
    test_connection()