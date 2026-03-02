""" Interface to Quicken-For-Mac data base"""

import sqlite3
import time

_qdb = None
_connection = None

_accounts = None
_categories = None
_payees = None
_securities = None

_dateFrom = None
_dateTo   = None
_restrictToAccounts = None
_restrictToCategories = None
_restrictToPayees = None
_restrictToSecurities = None

def open (qdbPath):
    """ Required first call.  Specifies the path to the Quicken database """
    global _qdb, _connection, _accounts, _categories, _payees, _securities
    _qdb = qdbPath
    _connection = sqlite3.connect ('file:' + _qdb + '?mode=ro', uri=True)
    _connection.row_factory = sqlite3.Row
    _accounts = _Accounts ()
    _categories = _Categories ()
    _payees = _Payees ()
    _securities = _Securities ()

def getAccounts ():
    """ Returns a list of accounts as an iterator. """
    return _accounts

def getCategories ():
    """ Returns a list of categories as an iterator """
    return _categories

def getPayees ():
    """ Returns a list of payees as an iterator """
    return _payees

def getTransactions ():
    """ Returns a list of transactions as an iterator """
    _transactions = _Transactions ()
    return _transactions

def getSecurities ():
    """ Returns a list of securities as an iterator """
    return _securities

def getQuotes (key):
    """ Returns a list of price quotes for given security as an iterator """
    return _Quotes(key)

def setRestrictToDates (dateFrom=None, dateTo=None):
    """ Restrict date range of subsequent queries.  Format is YYYY-MM-DD"""
    global _dateFrom, _dateTo
    _dateFrom = dateFrom
    _dateTo = dateTo
    return

def setRestrictToAccounts (restrictToAccounts):
    """ Restrict accounts used in subsequent queries.
         (Comma separated name list)."""
    global _restrictToAccounts
    _restrictToAccounts = restrictToAccounts
    return

def setRestrictToCategories (restrictToCategories):
    """ Restrict categories used in subsequent queries.
         (Comma separated name list)."""
    global _restrictToCategories
    _restrictToCategories = restrictToCategories
    return;

def setRestrictToPayees (restrictToPayees):
    """ Restrict payees used in subsequent queries.
         (Comma separated name list)."""
    global _restrictToPayees
    _restrictToPayees = restrictToPayees
    return

def setRestrictToSecurities (restrictToSecurities):
    """ Restrict securities used in subsequent queries.
         (Comma separated name list)."""
    global _restrictToSecurities
    _restrictToSecurities = restrictToSecurities
    return

def getPriceOnDate (securityName, date):
    """ Return security price on date, or most recent prior date. """
    """ Date format is YYYY-MM-DD."""
    price = 0.00
    nextPrice = 0.00
    cursor = _connection.cursor()
    SQL1 = 'select z_pk, zname from zsecurity where zname=?'
    c1 = cursor.execute (SQL1, (securityName,))
    SQL2 = 'select zquotedate, zclosingprice from zsecurityquote ' \
           + 'where zsecurity=? order by zquotedate'
    key = c1.fetchone()['z_pk']
    c2 = cursor.execute (SQL2, (str(key),))
    for qrow in (c2):
        qdate  = _formatQuickenDate (qrow['zquotedate'])
        nextPrice = float (qrow['zclosingprice'])
        if qdate == date:
            return nextPrice
        if qdate > date:
            return price
        price = nextPrice
    return nextPrice

def _formatQuickenDate (qtime):
    """ Convert Quicken time to YYYY-MM-DD format. """
    # Quicken's epoch is 2001,
    # 31 years after the UNIX epoch 1970 (978307200 seconds).
    qgmtime = time.gmtime(qtime + 978307200)
    return '{:4}-{:02}-{:02}'.format(qgmtime.tm_year,
                                     qgmtime.tm_mon,
                                     qgmtime.tm_mday)

def _convertToQuickenDate (date_string):
    """ Convert YYYY-MM-DD format to Quicken time. """
    # Quicken's epoch is 2001,
    # 31 years after the UNIX epoch 1970 (978307200 seconds).
    struct_time = time.strptime(date_string, '%Y-%m-%d')
    unix_time = time.mktime(struct_time)
    quicken_time = int(unix_time - 978307200)
    return quicken_time

def _column_exists(table_name, column_name):
    conn = None
    try:
        cursor = _connection.cursor()
        cursor.execute(f"PRAGMA table_info('{table_name}');")
        columns = cursor.fetchall()
        for col_info in columns:
            if col_info[1] == column_name:  # col_info[1] is the column name
                return True
        return False
    except sqlite3.Error as e:
        print(f"Error: {e}")
        return False

##############################################################################

class _Accounts:
    def __init__ (self):
        self.accounts = []
        self.cursor = _connection.cursor()
        SQL  = 'select zaccount.z_pk, zaccount.zname as name, '
        SQL += '       ztypename as type, '
        SQL += '       zusedinreports as usedInReports, '
        SQL += '       zsimpleinvesting as simpleInvesting '
        SQL += '       from zaccount '
        SQL += '       order by zaccount.zname asc'
        for row in self.cursor.execute (SQL):
            self.accounts.append ({'key':row['z_pk'],
                                   'name':row['name'],
                                   'type':row['type'],
                                   'usedInReports':row['usedInReports'],
                                   'simpleInvesting':row['simpleInvesting']
                                   })
    def __iter__ (self):
        self.counter=0
        return self
    def __next__ (self):
        while True:
            if self.counter >= len(self.accounts):
                raise StopIteration()
                return False
            else:
                a = self.accounts[self.counter]
                self.counter+=1
                return a
    def getKeyByName (self, name):
        for account in self.accounts:
            if account['name'] == name: return account['key']
        print ('Account:getKeyByName: Account not found: ', name)
        exit()


##############################################################################

class _Categories:
    def __init__ (self):
        self.cursor = _connection.cursor()
        SQL  = 'select z_pk, ztype, zname, zparentcategory from ztag'
        c = self.cursor.execute (SQL)
        temp = {}
        for row in c:
            temp[row['z_pk']] = {'key':      row['z_pk'],
                                 'name':     row['zname'],
                                 'type':     row['ztype'],
                                 'parentKey':row['zparentcategory']}
        path2key = {}
        for key in temp.keys():
            path = temp[key]['name']
            pKey = temp[key]['parentKey']
            while pKey is not None:
                path = temp[pKey]['name'] + ':' + path
                pKey = temp[pKey]['parentKey']
            path2key[path] = key
        self.categories = []
        for path in sorted(path2key.keys()):
            key = path2key[path]
            self.categories.append ({'key':temp[key]['key'],
                                     'path':path,
                                     'type':temp[key]['type']})
    def __iter__ (self):
        self.counter=0
        return self
    def __next__ (self):
        while True:
            if self.counter>=len(self.categories):
                raise StopIteration()
                return False
            else:
                c = self.categories[self.counter]
                self.counter+=1
                return c
    def getPathByKey (self, key):
        for category in self.categories:
            if category['key'] == key: return category['path']
        print ('Categories::getPathByKey: key not found: ', key)
        exit()
    def getKeyByPath (self, path):
        for category in self.categories:
            if category['path'] == path: return category['key']
        print ('Categories::getKeyByPath: path not found: ', path)
        exit()


##############################################################################

class _Payees:
    def __init__ (self):
        self.cursor = _connection.cursor()
    def __iter__ (self):
        SQL = 'select z_pk, zname from zuserpayee order by zname'
        self.cursor.execute (SQL)
        return self
    def __next__ (self):
        row = self.cursor.fetchone()
        if row==None: raise StopIteration()
        return {'key':row['z_pk'], 'name':row['zname']}
    def getKeyByName (self, name):
        print ('_Payees.getKeyByName not implemented yet.')
        exit()


##############################################################################

class _Securities:
    def __init__ (self):
        self.securities = []
        cursor = _connection.cursor()
        SQL = 'select z_pk, zname, ztype, zticker from zsecurity'
        c = cursor.execute (SQL)
        for row in c:
            if row['zticker']:
                self.securities.append ({'key': row['z_pk'],
                                         'name': row['zname'],
                                         'type': row['ztype'],
                                         'ticker': row['zticker']})
            else:
                self.securities.append ({'key': row['z_pk'],
                                         'name': row['zname'],
                                         'type': row['ztype'],
                                         'ticker': ''})

    def __iter__ (self):
        self.counter = 0
        return self
    def __next__ (self):
        if self.counter >= len(self.securities):
            raise StopIteration()
            return
        else:
            s = self.securities[self.counter]
            self.counter += 1
            return s
    def getKeyByName (self, name):
        print ('_Securities.getKeyByName not implemented yet.')
        exit()

##############################################################################

class _Quotes:
    def __init__ (self, key):
        self.key = key
    def __iter__ (self):
        self.cursor = _connection.cursor()
        SQL = 'select zquotedate, zclosingprice from zsecurityquote ' \
            + 'where zsecurity=? order by zquotedate'
        self.cursor.execute (SQL, (str(self.key),))
        return self
    def __next__ (self):
        qrow = self.cursor.fetchone()
        if qrow==None: raise StopIteration()
        row = {'date':  _formatQuickenDate (qrow['zquotedate']),
               'price': qrow['zclosingprice']}
        return row

##############################################################################

class _Transfers:
    def __init__ (self):
        self.transfers = {}
        self.cursor = _connection.cursor()
        SQL  = 'select '
        SQL += '  zcashflowtransactionentry.ztransfer, '
        SQL += '  zaccount.z_pk, '
        SQL += '  coalesce(zaccount.zname, zcashflowtransactionentry.ztransfer) as transfer '
        SQL += '  from zcashflowtransactionentry '
        SQL += '  left join zcashflowtransactionentry as splitTransfer '
        SQL += '    on splitTransfer.zquickenid = zcashflowtransactionentry.ztransfer '
        SQL += '  left join ztransaction '
        SQL += '    on ztransaction.z_pk = splitTransfer.zparent '
        SQL += '  left join zaccount '
        SQL += '    on zaccount.z_pk = ztransaction.zaccount '
        for row in self.cursor.execute (SQL):
            self.transfers[row['ztransfer']] = {'accountKey': row['z_pk'],
                                                'accountName': row['transfer']}

    def getAccountNameByTransferKey(self, key):
        if key in self.transfers:
            return self.transfers[key]['accountName']
        else:
            return None

    def getAccountKeyByTransferKey (self, key):
        if key in self.transfers:
            return self.transfers[key]['accountKey']
        else:
            return None

##############################################################################

class _UserTags:
    def __init__ (self):
        self.cursor = _connection.cursor()
        self.usertags = {}
        known_configs = [
            {'tagRelationship': 'z_15usertags',
             'tagTransaction': 'z_15cashflowtransactionentries',
             'tagInstance':    'z_76usertags'},
            {'tagRelationship': 'z_19usertags',
             'tagTransaction': 'z_19cashflowtransactionentries',
             'tagInstance': 'z_78usertags'},
            {'tagRelationship': 'z_20usertags',
             'tagTransaction':  'z_20cashflowtransactionentries',
             'tagInstance':     'z_79usertags'},
            {'tagRelationship': 'z_19usertags',
             'tagTransaction': 'z_19cashflowtransactionentries',
             'tagInstance': 'z_80usertags'},
        ]
        configs = known_configs + self._discover_configs(known_configs)
        success = False
        for i in configs:
            SQL  = 'select '
            SQL += '  zcashflowtransactionentry.z_pk, '
            SQL += '  ztag.zname '
            SQL += '  from zcashflowtransactionentry '
            SQL +=f'  join {i["tagRelationship"]} '
            SQL +=f'    on {i["tagRelationship"]}.{i["tagTransaction"]} = zcashflowtransactionentry.z_pk '
            SQL += '  join ztag '
            SQL +=f'    on ztag.z_pk = {i["tagRelationship"]}.{i["tagInstance"]} '
            try:
                u = self.cursor.execute (SQL)
            except sqlite3.OperationalError:
                continue
            else:
                success = True
                for row in u:
                    if row['z_pk'] in self.usertags.keys():
                        self.usertags[row['z_pk']]['names'] += ',' + row['zname']
                    else:
                        self.usertags[row['z_pk']] = {'key': row['z_pk'],
                                                      'names': row['zname']}
                break
        if not success:
            print('_UserTags not available. Data version is incompatible.')

    def _discover_configs (self, known_configs):
        """Inspect the schema to find z_%usertags relationship tables not already in known_configs."""
        known = {c['tagRelationship'] for c in known_configs}
        discovered = []
        try:
            rows = self.cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND LOWER(name) LIKE 'z_%usertags'"
            ).fetchall()
        except sqlite3.OperationalError:
            return discovered
        for row in rows:
            table_name = row[0].lower()
            if table_name in known:
                continue
            try:
                cols = [r[1].lower() for r in
                        self.cursor.execute(f'PRAGMA table_info({table_name})').fetchall()]
            except sqlite3.OperationalError:
                continue
            txn_cols = [c for c in cols if c.endswith('cashflowtransactionentries')]
            tag_cols = [c for c in cols if c.endswith('usertags')]
            if txn_cols and tag_cols:
                discovered.append({
                    'tagRelationship': table_name,
                    'tagTransaction':  txn_cols[0],
                    'tagInstance':     tag_cols[0],
                })
        return discovered

    def getUserTagNamesBySplitTransactionKey(self, key):
        if key in self.usertags:
            return self.usertags[key]['names']
        else:
            return None

##############################################################################

class _Transactions:
    def __init__ (self):
        self.counter=0
        self.dateTo = _dateTo
        self.dateFrom = _dateFrom
        self.A = _Accounts ()
        self.C = _Categories ()
        self.P = _Payees ()
        self.S = _Securities ()
        self.T = _Transfers ()
        self.U = _UserTags ()
        self.SQLconditional = ''
        self.business = (
            _column_exists('zcashflowtransactionentry', 'ZBUSINESS')
            and _column_exists('zbusiness', 'ZNAME')
            and _column_exists('zinvoicelineitem', 'ZAMOUNT')
        )

        if _restrictToAccounts != None:
            if self.SQLconditional == '':
                token = ' where ('
            else:
                token = ' or ('
            for accountName in _restrictToAccounts:
                self.SQLconditional += token + 'parentAccountKey=' \
                                    + str(self.A.getKeyByName(accountName))
                token = ' or '
            self.SQLconditional += ') '

        if _restrictToCategories != None:
            if self.SQLconditional == '':
                token = ' where ('
            else:
                token = ' and ('
            for categoryPath in _restrictToCategories:
                self.SQLconditional += token + 'splitCategoryKey=' \
                                    + str(self.C.getKeyByPath(categoryPath))
                token = ' or '
            self.SQLconditional += ') '

        if _restrictToPayees != None:
            if self.SQLconditional == '':
                token = ' where ('
            else:
                token = ' and ('
            for payeeName in _restrictToPayees:
                self.SQLconditional += token + 'parentAccountKey=' \
                                    + str(self.P.getKeyByName(payeeName))
                token = ' or '
            self.SQLconditional += ') '

        if _restrictToSecurities != None:
            if self.SQLconditional == '':
                token = ' where ('
            else:
                token = ' and ('
            for securityName in _restrictToSecurities:
                self.SQLconditional += token + 'parentAccountKey=' \
                                    + str(self.S.getKeyByName(securityName))
                token = ' or '
            self.SQLconditional += ') '

        if self.business:
            self.SQLOptionalColumns  = '  zbusiness.zname as splitBusinessName, '
            self.SQLOptionalColumns += '  zinvoicelineitem.zamount as splitClientPaymentAmount, '
            self.SQLOptionalRelationship  =  '  left join zbusiness '
            self.SQLOptionalRelationship +=  '    on zbusiness.z_pk = zcashflowtransactionentry.zbusiness '
            self.SQLOptionalRelationship +=  '  left join zcustomerpayment '
            self.SQLOptionalRelationship +=  '    on zcashflowtransactionentry.z_pk = zcustomerpayment.ztransactionentry '
            self.SQLOptionalRelationship +=  '  left join zcustomerpaymentallocation '
            self.SQLOptionalRelationship +=  '    on zcustomerpayment.z_pk = zcustomerpaymentallocation.zcustomerpayment '
            self.SQLOptionalRelationship +=  '  left join zinvoice '
            self.SQLOptionalRelationship +=  '    on zcustomerpaymentallocation.zinvoice = zinvoice.z_pk '
            self.SQLOptionalRelationship +=  '  left join zinvoicelineitem '
            self.SQLOptionalRelationship +=  '    on zinvoice.z_pk = zinvoicelineitem.zinvoice '
        else:
            self.SQLOptionalColumns = self.SQLOptionalRelationship = ''

    def __iter__ (self):
        self.cursor = _connection.cursor()
        # Not all of the following fields are used (yet).
        SQL  = 'select '
        SQL += '  ztransaction.z_pk                 as transactionKey, '
        SQL += '  ztransaction.zaccount             as parentAccountKey, '
        SQL += '  ztransaction.zentereddate         as parentDate, '
        SQL += '  ztransaction.zchecknumber         as parentCheckNumber, '
        SQL += '  ztransaction.zuserpayee           as parentPayeeKey, '
        SQL += '  ztransaction.zamount              as parentAmount, '
        SQL += '  ztransaction.znote                as parentNote, '
        SQL += '  ztransaction.zposition            as parentPositionKey, '
        SQL += '  ztransaction.zunits               as parentSecurityShares, '
        SQL += '  zaccount.zname                    as parentAccountName, '
        SQL += '  zuserpayee.zname                  as parentPayeeName, '
        SQL += '  zposition.zsecurity               as parentSecurityKey, '
        SQL += '  zsecurity.zname                   as parentSecurityName, '
        SQL += '  zsecurity.zticker                 as parentSecurityTicker, '
        SQL += '  ztransaction.ztype                as parentTypeKey, '
        SQL += '  ztransaction.zcommission          as parentCommission, '
        SQL += '  ztransaction.zcostbasis           as parentCostBasis, '
        SQL += self.SQLOptionalColumns
        SQL += '  zcashflowtransactionentry.zparent as splitParentKey, '
        SQL += '  zcashflowtransactionentry.zcategorytag  '
        SQL += '                                    as splitCategoryKey, '
        SQL += '  zcashflowtransactionentry.zamount as splitAmount, '
        SQL += '  zcashflowtransactionentry.znote   as splitNote, '
        SQL += '  ztransaction.znumerator           as stockSplitNumerator, '
        SQL += '  ztransaction.zdenominator         as stockSplitDenominator, '
        SQL += '  zcashflowtransactionentry.ztransfer  '
        SQL += '                                    as splitTransferKey, '
        SQL += '  zcashflowtransactionentry.z_pk    as splitTransactionKey '
        SQL += '  from  ztransaction '
        SQL += '  left join zcashflowtransactionentry '
        SQL += '    on ztransaction.z_pk = zcashflowtransactionentry.zparent '
        SQL += '  left join zaccount '
        SQL += '    on zaccount.z_pk = ztransaction.zaccount '
        SQL += '  left join zuserpayee '
        SQL += '    on zuserpayee.z_pk = ztransaction.zuserpayee '
        SQL += '  left join zposition '
        SQL += '    on zposition.z_pk = ztransaction.zposition '
        SQL += '  left join zsecurity '
        SQL += '    on zsecurity.z_pk = zposition.zsecurity '
        SQL += self.SQLOptionalRelationship
        SQL += self.SQLconditional
        SQL += '       order by parentDate asc'
        self.cursor.execute (SQL)
        return self
    def __next__ (self):
        while True:
            trans = self.cursor.fetchone()
            if trans==None: raise StopIteration()
            if trans['splitAmount']==None: continue
            row = {'key':            trans['transactionKey'],
                   'date':           _formatQuickenDate (trans['parentDate']),
                   'amount':         trans['splitAmount'],
                   'accountKey':     trans['parentAccountKey'],
                   'payeeKey':       trans['parentPayeeKey'],
                   'categoryKey':    trans['splitCategoryKey'],
                   'accountName':    trans['parentAccountName'],
                   'categoryPath':   \
                               self.C.getPathByKey(trans['splitCategoryKey']),
                   'payeeName':      trans['parentPayeeName'],
                   'securityShares': trans['parentSecurityShares'],
                   'securityKey':    trans['parentSecurityKey'],
                   'securityName':   trans['parentSecurityName'],
                   'securityTicker': trans['parentSecurityTicker'],
                   'parentNote':     trans['parentNote'],
                   'typeKey':        trans['parentTypeKey'],
                   'commission':     trans['parentCommission'],
                   'costbasis':      trans['parentCostBasis'],
                   'splitNote':      trans['splitNote'],
                   'numerator':      trans['stockSplitNumerator'],
                   'denominator':    trans['stockSplitDenominator'],
                   'transferAcctName':  \
                              self.T.getAccountNameByTransferKey(trans['splitTransferKey']),
                   'transferAcctKey':   \
                              self.T.getAccountKeyByTransferKey(trans['splitTransferKey']),
                   'tags':              \
                              self.U.getUserTagNamesBySplitTransactionKey(trans['splitTransactionKey'])
                   }
            if self.business:
                row['business'] = trans['splitBusinessName']  # business name
                if trans['splitClientPaymentAmount'] != None:  row['amount'] = trans['splitClientPaymentAmount']  # client payment amount
            if row['payeeKey']==None:  row['payeeKey']=''
            if row['payeeName']==None: row['payeeName']=''
            if row['parentNote']==None: row['parentNote']=''
            if row['transferAcctName']==None: row['transferAcctName']=''

            if self.dateFrom != None and row['date']<self.dateFrom: continue
            if self.dateTo   != None and row['date']>self.dateTo:   continue
            return row
