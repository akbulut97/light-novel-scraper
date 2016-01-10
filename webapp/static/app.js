/*jshint strict: true*/

var title = 'Light Novel Scrapper';

var app = angular.module('lightScrapApp', []);

app.config(function ($interpolateProvider) {
    'use strict';
    $interpolateProvider.startSymbol('//');
    $interpolateProvider.endSymbol('//');
});

app.factory('novelTasks', ['$http', function ($http) {
    'use strict';
    return {
        queue: function (novelInfo) {
            return $http.post('/task/', JSON.stringify(novelInfo));
        },
        status: function (taskId) {
            return $http.get('/task/' + taskId);
        },
        chapters: function (taskId) {
            return $http.get('/task/' + taskId + '/chapters/');
        }
    };
}]);

app.factory('epubTasks', ['$http', function ($http) {
    'use strict';
    return {
        queue: function (taskId) {
            return $http.post('/task/' + taskId + '/chapters/task/epub/', {});
        },
        status: function (taskId, epubTaskId) {
            return $http.get('/task/' + taskId + '/chapters/task/epub/' + epubTaskId);
        },
        download: function (taskId, title) {
            window.location = '/task/' + taskId + '/chapters/d/epub/?title=' + title;
        }
    };
}]);


app.controller('HeadController', function () {
    'use strict';
    var vm = this;
    vm.title = title;
});


app.controller('MainController', ['$interval', '$http', 'novelTasks', 'epubTasks', function ($interval, $http, novelTasks, epubTasks) {
    'use strict';
    var vm = this;
    vm.title = title;
    vm.results = null;
    vm.htmlReady = false;
    vm.epubReady = false;
    vm.zipDownloadLink = null;
    vm.epub_results = null;
    vm.taskId = null;
    vm.celeryStatus = false;
    vm.progressBar = 0;
    vm.scrapForm = {
        'title': 'smartphone',
        'start': 31,
        'end': 33,
        'url': 'http://raisingthedead.ninja/2015/10/06/smartphone-chapter-31/'
    };
    vm.current_chapter = vm.scrapForm.start;
    $http.get('/ping')
        .success(function (res) {
            if (res != 'null'){
              vm.celeryStatus = true;
            }
        });
    vm.submitScrapRequest = function () {
        vm.hideSubmit = true;
        novelTasks.queue({
            'title': vm.scrapForm.title,
            'start': vm.scrapForm.start,
            'end': vm.scrapForm.end,
            'url': vm.scrapForm.url
        })
            .success(function (res) {
                var novelStatusChecker;
                if (res.status === 'success') {
                    vm.results = 'Checking status';
                    var progressTotal = (parseInt(vm.scrapForm.end) - parseInt(vm.scrapForm.start)) + 1;
                    var progressDiff = 0;
                    var prevChapter = parseInt(vm.scrapForm.start) - 1;
                    vm.progressBar = progressDiff / progressTotal;
                    novelStatusChecker = $interval(function () {
                        console.log('checking');
                        vm.taskId = res.taskId;
                        novelTasks.status(vm.taskId)
                            .success(function (statusRes) {
                                vm.results = statusRes;
                                if (statusRes.state === 'SUCCESS') {
                                    vm.progressBar = 100;
                                    vm.current_chapter = vm.scrapForm.end;
                                    vm.hideSubmit = false;
                                    $interval.cancel(novelStatusChecker);
                                    vm.htmlReady = true;
                                    vm.zipDownloadLink = '/task/' + vm.taskId + '/chapters/d/zip/';
                                }
                                else if (statusRes.state === 'PROGRESS') {

                                    vm.current_chapter = statusRes.info.current_chapter;
                                    if (parseInt(vm.current_chapter) > prevChapter){
                                        progressDiff++;
                                        vm.progressBar = progressDiff / progressTotal * 100;
                                        prevChapter++;
                                        console.log(vm.progressBar);
                                    }

                                    console.log(vm.progressBar);
                                }
                            })
                            .error(function (statusErr) {
                                console.log(statusErr);
                            });
                    }, 1000);
                }

            })
            .error(function (err) {
                console.log(err);
            });
    };
    vm.submitePubRequest = function () {
        epubTasks.queue(vm.taskId)
            .success(function (res) {
                vm.epubReady = true;
                var epubStatusChecker;
                console.log(res);
                vm.epub_results = res;
                epubStatusChecker = $interval(function () {
                    console.log('checking epub status');
                    epubTasks.status(vm.taskId, res.epubTaskId)
                        .success(function (statusRes) {
                            vm.epubResults = statusRes;
                            if (statusRes.state === 'SUCCESS') {
                                $interval.cancel(epubStatusChecker);
                                console.log('grabbing %s', vm.taskId);
                                epubTasks.download(vm.taskId, vm.scrapForm.title);
                                vm.epubReady = false;
                            }
                        })
                        .error(function (err) {
                            console.log(err);
                        });
                }, 1000);
            })
            .error(function (err) {
                console.log(err);
            });
    };


}]);
