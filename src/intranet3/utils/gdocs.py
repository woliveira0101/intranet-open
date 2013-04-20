# -*- coding: utf-8 -*-
"""
Helpers for dealing with google docs
"""
import time
import math

from gdata.spreadsheet.service import SpreadsheetsService, CellQuery
from gdata.spreadsheet import SpreadsheetsCellsFeed

from intranet3.log import ERROR_LOG, INFO_LOG

ERROR = ERROR_LOG(__name__)
DEBUG = INFO_LOG(__name__)

MAX_ROWS_PER_BATCH = 100

class CellDict(object):
    
    def __init__(self, client, key, worksheet_id, start_row, end_row):
        self.entries = {}
        self.batch = SpreadsheetsCellsFeed()
        self.max_col = 0
        self.max_row = 0
        self.client = client
        
        query = CellQuery()
        query.return_empty = 'true'
        query.min_row = str(start_row)
        query.max_row = str(end_row)
        self.cells = client.GetCellsFeed(key, worksheet_id, query=query)
        self.register_all(self.cells.entry)
        
    def register_all(self, entries):
        for entry in entries:
            row = int(entry.cell.row)
            col = int(entry.cell.col)
            self.entries[row - 1, col - 1] = entry
        
    def register(self, row, col, cell):
        if row > self.max_row:
            self.max_row = row
        if col > self.max_col:
            self.max_col = col
        self.entries[row, col] = cell
        
    def __setitem__(self, (row, col), value):
        entry = self.entries[row, col]
        if isinstance(value, (int, float, long)): 
            entry.cell.inputValue = str(value).replace('.', ',')
        else:
            entry.cell.inputValue = value
        self.batch.AddUpdate(entry)
        
    def perform(self):
        updated = self.client.ExecuteBatch(self.batch, self.cells.GetBatchLink().href)
        for entry in updated.entry:
            assert entry.batch_status.code == '200', u"Error status %s, %s" % (entry.batch_status.code.decode('utf-8'), entry.batch_status.reason.decode('utf-8'))

def insert_or_replace_worksheet(email, password, key, worksheet_name, headers, rows):
    #DEBUG(u"MEM 1 %s" % helpers.get_mem_usage())
    start = time.time()
    DEBUG(u'Attempting to authenticate as %s for worksheet %s' % (email, key))
    client = SpreadsheetsService(email, password)
    client.ProgrammaticLogin()
    #DEBUG(u"MEM 2 %s" % helpers.get_mem_usage())
    DEBUG(u'Authenticated, will search for %s sheet' % (worksheet_name, ))
    worksheets = client.GetWorksheetsFeed(key)
    #DEBUG(u"MEM 3 %s" % helpers.get_mem_usage())
    for worksheet in worksheets.entry:
        if worksheet.title.text == worksheet_name:
            DEBUG(u'Worksheet found, attempting delete')
            client.DeleteWorksheet(worksheet)
            DEBUG(u'Worksheet deleted')
            # break - remove also duplicated sheets
    DEBUG(u'Attempting to insert new sheet')
    #DEBUG(u"MEM 4 %s" % helpers.get_mem_usage())
    worksheet = client.AddWorksheet(worksheet_name, len(rows) + 1, len(headers), key)
    worksheet_id = worksheet.id.text.rsplit('/', 1)[-1]
    DEBUG(u'Inserted new sheet %s' % (worksheet_id, ))
    # sending ALL changes at once uses too much memory on constructing the XML request
    # and parsing response, we must perform several batch queries instead of just one
    # to keep memory usage at bay.
    
    # first insert headers
    DEBUG(u'Preparing headers batch')
    #DEBUG(u"MEM 5 %s" % helpers.get_mem_usage())
    cell_dict = CellDict(client, key, worksheet_id, 1, 1)
    #DEBUG(u"MEM 6 %s" % helpers.get_mem_usage())
    for i, header in enumerate(headers):
        cell_dict[0, i] = header
    #DEBUG(u"MEM 7 %s" % helpers.get_mem_usage())
    DEBUG(u'Will send headers batch')
    cell_dict.perform()
    DEBUG(u'Headers batch sent')
    #DEBUG(u"MEM 8 %s" % helpers.get_mem_usage())

    # then insert rows, batch at a time
    for i in xrange(int(math.ceil(float(len(rows)) / MAX_ROWS_PER_BATCH))):
        DEBUG(u'Preparing batch %s' % i)
        #DEBUG(u"MEM 9 %s" % helpers.get_mem_usage())
        part = rows[i * MAX_ROWS_PER_BATCH : (i + 1) * MAX_ROWS_PER_BATCH]
        cell_dict = CellDict(client, key, worksheet_id, 1 + i * MAX_ROWS_PER_BATCH, 1 + min(len(rows), (i + 1) * MAX_ROWS_PER_BATCH))
        #DEBUG(u"MEM 10 %s" % helpers.get_mem_usage())
        for y, row in enumerate(part, i * MAX_ROWS_PER_BATCH):
            for x, col in enumerate(row):
                cell_dict[y + 1, x] = col
        #DEBUG(u"MEM 11 %s" % helpers.get_mem_usage())
        DEBUG(u'Will send batch %s (%s rows)' % (i, len(part)))
        cell_dict.perform()
        DEBUG(u'Batch %s sent (%s rows)' % (i, len(part)))
        #DEBUG(u"MEM 12 %s" % helpers.get_mem_usage())
    DEBUG("All batches sent (%s rows)" % len(rows))
    
    #DEBUG(u"MEM 13 %s" % helpers.get_mem_usage())
    DEBUG(u'Worksheet replaced successfully in %0.2f s' % (time.time() - start, ))
