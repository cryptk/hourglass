String.prototype.capitalize = function() {
    return this.charAt(0).toUpperCase() + this.slice(1);
}

document.filterlist = {};

var addFormGroup = function(name) {
    filterdiv = $('<div class="form-group"></div>').appendTo( $('#filters') );
    labeldiv = $('<label for="'+name+'-filter">'+name.capitalize()+'</label>').appendTo( $(filterdiv) );
    formitem = $('<select data-filter="'+name+'" class="form-control" id="'+name+'-filter"><option value=""></option></select>').appendTo($(labeldiv));
    formitem.on('change', function() {
        updateDataTablesUrl();
        document.eventstable.ajax.reload(null, false);
    });
}

var addFilters = function() {
    $('#filters').addClass('form-inline');
    addFormGroup('status');
    addFormGroup('datacenter');
    addFormGroup('checkname');
}

var addOption = function(selectID, option, value=null) {
    if (value === null) {
        value = option;
    }
    console.log(option, value);
    if ( $('#'+selectID+':has(option[value='+value+'])').length == 0) {
        $('#'+selectID).append('<option value="'+value+'">'+option+'</option>');
    }
}

var updateFilters = function() {

    $.getJSON('/api/events/checks', function(data) {
        $.each(data.checks, function(idx, obj) {
            addOption('checkname-filter', obj);
        });
    });
    $.getJSON('/api/events/datacenters', function(data) {
        $.each(data.datacenters, function(idx, obj) {
            addOption('datacenter-filter', obj);
        });
    });
}

var updateDataTablesUrl = function() {
    params = {}
    $('#filters select').each(function(idx, obj) {
        params[$(obj).data('filter')] = $(obj).children('option:selected').val()
    });
    document.eventstable.ajax.url('/api/events?'+$.param(params));
}

$(document).ready(function() {
    statusclasses = {
        'OK': 'success',
        'Warning': 'warning',
        'Critical': 'danger'
    }
    statusnames = {
        0: 'OK',
        1: 'Warning',
        2: 'Critical'
    }
    document.eventstable = $('#events').DataTable({
        'lengthMenu': [ [25, 50, 100, -1], [25, 50, 100, "All"] ],
        //'stateSave' : true,
        'columnDefs': [
            {
                "targets": [ 0 ],
                "visible": false,
                "searchable": true
            },
        ],
        'order': [
            [ 0, 'asc' ],
            [ 5, 'desc' ],
        ],
        'ajax': {
            url: '/api/events',
            dataSrc: 'events'
        },
        'dom': "<'row'<'col-sm-2'l><'col-sm-8'<'#filters'>><'col-sm-2'f>><'row'<'col-sm-12'tr>><'row'<'col-sm-5'i><'col-sm-7'p>>",
        'columns': [
            {data: 'check.status',
             name: 'status'},
            {data: 'datacenter',
             name: 'datacenter'},
            {data: 'client.name',
             name: 'source'},
            {data: 'check.name',
             name: 'check-name'},
            {data: 'check.output',
             name: 'check-output'},
            {data: 'occurrences',
             name: 'occurrences'},
            {data: 'timestamp',
             name: 'timestamp'},
        ],
        'fnRowCallback': function( nRow, aData, iDisplayIndex, iDisplayIndexFull ) {
            $(nRow).addClass(statusclasses[aData['check']['status']]);
            var d = new Date(0);
            d.setUTCSeconds(aData['timestamp']);
            $('td:last', nRow).html('<time class="timeago" datetime="'+d.toISOString()+'">'+d+'</time>');
        },
        'fnDrawCallback': function(oSettings){
            $('time.timeago').timeago();
        },
        'createdRow': function(nRow, aData, iDataIndex) {
            aData['check']['status'] = statusnames[aData['check']['status']];
            $(nRow).data('href', aData['href']);
            $(nRow).click(function() {
                window.open($(this).data("href"), '_blank');
            });
        },
        'initComplete': function () {
            addFilters();
            updateFilters();
            $([['Critical', 2],['Warning', 1],['OK', 0]]).each( function(idx, obj) {
                console.log(obj);
                addOption('status-filter', obj[0], obj[1])
            });
            setInterval( function() {
                updateDataTablesUrl()
                updateFilters();
                document.eventstable.ajax.reload(null, false);
            }, 3000);
        }
    });
});
