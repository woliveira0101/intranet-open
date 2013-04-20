(function() {
    var initializing = false, fnTest = /xyz/.test(function() { xyz;
    }) ? /\b_super\b/ : /.*/;
    this.Class = function() {
    };

    Class.extend = function(prop) {
        var _super = this.prototype;

        // Instantiate a base class (but only create the instance,
        // don't run the init constructor)
        initializing = true;
        var prototype = new this();
        initializing = false;

        // Copy the properties over onto the new prototype
        for (var name in prop) {
            prototype[name] = typeof prop[name] == "function"&& typeof _super[name] == "function"&&fnTest.test(prop[name]) ? (function(name,fn) {
                return function() {
                    var tmp = this._super;
                    this._super = _super[name];
                    var ret = fn.apply(this,arguments);
                    this._super = tmp;
                    return ret;
                };
            })(name,prop[name]) : prop[name];
        }

        function Class() {
            if (!initializing&&this.init)
                this.init.apply(this,arguments);
        }


        Class.prototype = prototype;
        Class.prototype.constructor = Class;
        Class.extend = arguments.callee;

        return Class;
    };

    var guid = function() {
        var u = function() {
            return (Math.random()*(1 << 32)).toString(36).replace('.','');
        }
        return function() {
            return u()+u();
        }
    }();
    var Event = Class.extend({
        init: function(name,obj) {
            this.isFire = false;
            this.name = name;
            this.obj = obj||null;
            this.listeners = [];
        },
        add: function(fn,bind,args) {
            bind = bind||this.obj;

            if (this.find(fn,bind) == -1) {
                this.listeners.push({
                    fn:fn,
                    bind:bind,
                    args:args
                });
            }
        },
        find: function(fn,bind) {
            var l;
            for (var i = 0, l = this.listeners.length;i < l;++i) {
                l = this.listeners[i];
                if (l) {
                    if (l.fn == fn&&(l.bind == (bind||this.obj))) {
                        return i;
                    }
                }
            }
            return -1;
        },
        remove: function(fn,bind) {
            if (bind) {
                var i = this.find(fn,bind);
                if (i != -1) {
                    this.listeners.splice(i,1);
                }
            }
        },
        clear: function() {
            this.listeners = {};
        },
        fire: function() {
            if (!this.isFire) {
                this.isFire = true;
                args = Array.prototype.slice.call(arguments);
                for (var i = 0, len = this.listeners.length;i < len;++i) {
                    var l = this.listeners[i];
                    if (l.fn.apply(l.bind,args) === false) {
                        this.isFire = false;
                        return false;
                    }

                }
                this.isFire = false;
            }
            return true;
        }
    });

    var Events = Class.extend({

        addEvent: function(en,fn,bind) {
            bind = bind||this;
            this._events = this._events|| {};
            en = en.toLowerCase();
            var e = this._events[en];
            if (!e) {
                e = this._events[en] = new Event(en,this);
            }
            e.add(fn,bind);
        },
        addEvents: function(obj,bind) {
            for (var i in obj) {
                this.addEvent(i,obj[i],bind);
            }
        },
        removeEvent: function(en,fn,bind) {
            this._events = this._events|| {};
            en = en.toLowerCase();
            var e = this._events[en];
            if (e) {
                e.remove(fn,bind);
            }
        },
        fireEvent: function() {
            this._events = this._events|| {};

            var args = Array.prototype.slice.call(arguments);
            var en = args.shift();
            en = en.toLowerCase();
            var e = this._events[en];
            if (e) {
                return e.fire.apply(e,args);
            }
            return null;
        },
        clearEvents: function(en) {
            en = en.toLowerCase();
            var e = this._events[en];
            if (e) {
                e.clear();
            }
        }
    });

    var Uploader = Class.extend({
        init: function(el,options) {
            this._adapter = null;
            this._button(el);
            this.options = $.extend({
                autoSend:true,
                url:'/upload/',
                onAdd: function(e) {
                },
                onProgress: function(e) {
                },
                onLoad: function(e) {
                },
                onComplete: function(e) {
                },
                onError: function(e) {
                }
            },options);

        },
        _button: function(el) {
            var $el = $(el);
            if ($el.length) {
                $el.addClass('x-upload-button-wrapper');
                this.$btn = $('<div class="x-upload-button"></div>');
                $el.append(this.$btn);
                this._createInput();
            }
        },
        _createInput: function() {
            this.$btn.html('');
            var $input = $('<input class="file" type="file" name="file" />');
            this.$btn.append($input);
            $input.bind('change',$.proxy(this._onChange,this));
            this.input = $input.get(0);
        },
        _onChange: function() {
            this.getAdapter().addInput(this.input);
            this._createInput();
        },
        getAdapter: function() {
            if (!this._adapter) {
                this._adapter = Uploader.isModern ? new XHRAdapter(this.options) : new FormAdapter(this.options);
            }
            return this._adapter;
        }
    });

    var Adapter = Events.extend({
        init: function(options) {
            this.options = options;
            this._queue = [];
            this.addEvent('add',this.options.onAdd);
            this.addEvent('progress',this.options.onProgress);
            this.addEvent('load',this.options.onLoad);
            this.addEvent('complete',this.options.onComplete);
            this.addEvent('error',this.options.onError);
        },

        addRes: function(file) {
            file.id = guid();
            this._queue.push(file);
            this.fireEvent('add',file);
            if (this.options.autoSend) {
                this.next();
            }
        },
        send: function() {
            this.next();
        },
        next: function() {
            if (this._isSending) {
                return;
            }

            if (!this._queue.length) {
                this.fireEvent('complete');
                return;
            }
            this._isSending = true;

            var file = this._queue.shift();
            this.sendFile(file,$.proxy(function() {
                this._isSending = false;
                this.next();
            },this));

        },
        sendFile: function(file,fn) {
            throw new Error('Not implement Adapter::send(e,fn)');
        },
        addInput: function(input) {
            throw new Error('Not implement Adapter::addInput(input)');
        }
    });

    var buildMessage = function(data,boundary) {
        var CRLF = "\r\n";
        var parts = [];
        for (var i = 0;i < data.length;i++) {
            var item = data[i];

            var part = 'Content-Disposition: form-data; ';
            if (item.type == 'file') {
                var mime = item.mime ? item.mime : 'application/octet-stream';
                part += 'name="'+item.name+'"; filename="'+item.filename+'"'+CRLF;
                part += 'Content-Type: '+mime;
            } else {
                part += 'name="'+item.name+'"';
            }
            part += CRLF+CRLF;
            part += item.data+CRLF;
            parts.push(part);
        }
        return '--'+boundary+CRLF+parts.join('--'+boundary+CRLF)+'--'+boundary+'--'+CRLF;
    };
    var XHRAdapter = Adapter.extend({
        init: function(uploader) {
            this._super(uploader);
            this._isSending = false;

        },

        addInput: function(input) {
            for (var i = 0;i < input.files.length;i++) {
                var file = input.files[i];
                var d = {
                    name:file.fileName||file.name,
                    size:file.fileSize||file.size,
                    mime:file.type,
                    file:file
                };
                this.addRes(d);
            }
        },
        sendFile: function(e,fn) {
            var file = e.file;
            var xhr = new XMLHttpRequest();
            var s = this;
            xhr.upload.onprogress = function(ev) {
                if (ev.lengthComputable) {
                    s.fireEvent('progress', {
                        id:e.id,
                        loaded:ev.loaded,
                        total:ev.total
                    });
                }
            }
            xhr.onreadystatechange = function() {
                if (xhr.readyState == 4) {
                    try {
                        if (xhr.status !== 200) {
                            throw new Error('System error');
                        }
                        var res = null;
                        try {
                            res = eval("("+xhr.responseText+")");
                        } catch(e) {
                            throw new Error('Incorect response. Expected: JSON');
                        }
                        if (res.status == 'ok'&&res.file) {
                            s.fireEvent('load', {
                                id:e.id,
                                file:res.file
                            });
                        } else {
                            throw new Error(res.msg||res);
                        }
                    } catch(e) {
                        s.fireEvent('error', {
                            id:e.id,
                            msg:e
                        });
                    }
                    fn();
                }
            };

            var boundary = 'BOUNDARY--------------'+(new Date).getTime();

            xhr.open("POST",this.options.url,true);
            xhr.setRequestHeader("Cache-Control","no-cache");
            xhr.setRequestHeader("X-Requested-With","XMLHttpRequest");
            xhr.setRequestHeader("X-File-Name",encodeURIComponent(e.name));
            xhr.setRequestHeader("Content-Type","multipart/form-data; boundary="+boundary);
            var reader = new FileReader();
            reader.onload = function(ev) {
                var data = buildMessage([{
                    type:'file',
                    data:ev.target.result,
                    mime:e.mime,
                    filename:e.name,
                    name:'file'
                }],boundary);
                xhr.send(data);
            };
            reader.readAsDataURL(e.file);
        }
    });
    var FormAdapter = Adapter.extend({
        sendFile: function(e,fn) {
            var form = this._createForm();
            var iframe = this._createIFrame();
            var s = this;
            iframe.bind('load', function(e) {
                var str = iframe.contents().find('body').html();
                
                var res = eval("("+str+")");
                console.log()
                if (res.status == 'ok'&&res.file) {
                    s.fireEvent('load', {
                        id:e.id,
                        file:res.file
                    });
                    iframe.remove();
                    form.remove();
                    fn();
                } else {
                    s.fireEvent('error', {
                        id:e.id,
                        msg:res.error
                    });
                    iframe.remove();
                    form.remove();
                    fn();
                }
            });
            form.attr('target',iframe.attr('name'));
            form.append(e.input);
            form.submit();

        },
        addInput: function(input) {
            this.addRes({
                name:input.value,
                input:input
            });
        },
        _createForm: function() {
            var form = $('<form action="'+this.options.url+'" style="display:none" method="post" enctype="multipart/form-data"></form>');
            $(document.body).append(form);
            return form;
        },
        _createIFrame: function() {
            var sid = guid();
            var iframe = $('<iframe style="display:none" src="javascript:false;" name="'+sid+'" id="'+sid+'" />');
            $(document.body).append(iframe);
            return iframe;
        }
    });

    Uploader.isModern = (function() {var i = $('<input type="file" />');         return 'multiple' in i.get(0);    })();

    $(function() {
        var $btn = $('#upload-btn');
        var href = $btn.attr('data-href');
        $btn.show();
        var up = new Uploader($btn, {
            url:href,
            onAdd: function(e) {
                $('#upload-progress').show().css('width','0%');
            },
            onProgress: function(e) {
                $('#upload-progress').css('width',parseInt(e.loaded/e.total*100,10)+'%');
            },
            onLoad: function(e) {
                $('#my-avatar img').attr('src',e.file.url+'&t='+(new Date().getTime()));
                $('input#avatar').attr('value',1);
            },
            onComplete: function(e) {
                $('#upload-progress').hide();
            },
            onError: function(e) {
                
            }
        });
        return false;
    });

})();
