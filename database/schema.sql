-- 广厦有备 SQLite schema; initialize data with backend.database.
CREATE TABLE account(dataset TEXT,year TEXT,granted REAL DEFAULT 0,used REAL DEFAULT 0,expired REAL DEFAULT 0,entitlement REAL DEFAULT 0,PRIMARY KEY(dataset,year));

CREATE TABLE daily(dataset TEXT,day TEXT,payload TEXT,PRIMARY KEY(dataset,day));

CREATE TABLE events(id INTEGER PRIMARY KEY,at TEXT,dataset TEXT,kind TEXT,payload TEXT);

CREATE TABLE grants(dataset TEXT,year TEXT,period TEXT,amount REAL,payload TEXT,PRIMARY KEY(dataset,year,period));

CREATE TABLE policy_state(dataset TEXT,year TEXT,closed INTEGER DEFAULT 0,PRIMARY KEY(dataset,year));

CREATE TABLE runs(id TEXT PRIMARY KEY,dataset TEXT,payload TEXT);

CREATE TABLE stock(item TEXT PRIMARY KEY,quantity INTEGER);

CREATE TABLE uses(redemption_id TEXT PRIMARY KEY,dataset TEXT,year TEXT,item TEXT,cost REAL,status TEXT,at TEXT);
