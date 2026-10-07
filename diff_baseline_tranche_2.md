Up to random card selection the steps were identical.
Random card selection gave a different card. So the snapshot after tranche 2 differs from the baseline session.

```
--- baseline_session.json
+++ after_tranche_2.json
@@ -10,16 +10,6 @@
   "groups": [
     {
       "card_ids": [
-        "Data Science & ML Fundamentals:5",
-        "Data Science & ML Fundamentals:7",
-        "Data Science & ML Fundamentals:8",
-        "Data Science & ML Fundamentals:9",
-        "Data Science & ML Fundamentals:10",
-        "Data Science & ML Fundamentals:14",
-        "Data Science & ML Fundamentals:17",
-        "Data Science & ML Fundamentals:19",
-        "Data Science & ML Fundamentals:24",
-        "Data Science & ML Fundamentals:26",
         "Github & Version Control Workflows:21"
       ],
       "color": "#f542b3",
@@ -27,12 +17,7 @@
       "name": "git"
     },
     {
-      "card_ids": [
-        "Data Science & ML Fundamentals:4",
-        "Data Science & ML Fundamentals:1",
-        "Data Science & ML Fundamentals:21",
-        "Data Science & ML Fundamentals:3"
-      ],
+      "card_ids": [],
       "color": "#424ef5",
       "id": "group-2",
       "name": "ML types"
@@ -48,67 +33,20 @@
     },
     {
       "card_ids": [
-        "Github & Version Control Workflows:22"
+        "Database & SQL Fundamentals:9"
       ],
-      "color": "#42f553",
+      "color": "#19cc55",
       "id": "group-5",
       "name": "B"
     },
     {
-      "card_ids": [
-        "Github & Version Control Workflows:22"
-      ],
-      "color": "#f5f442",
+      "card_ids": [],
+      "color": "#f54245",
       "id": "group-5",
       "name": "C"
     }
   ],
   "links": [
-    {
-      "group_id": null,
-      "source_id": "Data Science & ML Fundamentals:10",
-      "target_id": "Data Science & ML Fundamentals:24"
-    },
-    {
-      "group_id": null,
-      "source_id": "Data Science & ML Fundamentals:10",
-      "target_id": "Data Science & ML Fundamentals:5"
-    },
-    {
-      "group_id": null,
-      "source_id": "Data Science & ML Fundamentals:19",
-      "target_id": "Data Science & ML Fundamentals:17"
-    },
-    {
-      "group_id": null,
-      "source_id": "Data Science & ML Fundamentals:26",
-      "target_id": "Data Science & ML Fundamentals:17"
-    },
-    {
-      "group_id": null,
-      "source_id": "Data Science & ML Fundamentals:26",
-      "target_id": "Data Science & ML Fundamentals:8"
-    },
-    {
-      "group_id": null,
-      "source_id": "Data Science & ML Fundamentals:5",
-      "target_id": "Data Science & ML Fundamentals:7"
-    },
-    {
-      "group_id": null,
-      "source_id": "Data Science & ML Fundamentals:5",
-      "target_id": "Data Science & ML Fundamentals:8"
-    },
-    {
-      "group_id": null,
-      "source_id": "Data Science & ML Fundamentals:9",
-      "target_id": "Data Science & ML Fundamentals:14"
-    },
-    {
-      "group_id": null,
-      "source_id": "Data Science & ML Fundamentals:9",
-      "target_id": "Data Science & ML Fundamentals:8"
-    },
     {
       "group_id": null,
       "source_id": "Database & SQL Fundamentals:1",
@@ -237,18 +175,18 @@
   "progress": [
     {
       "card_id": "Data Science & ML Fundamentals:1",
-      "difficulty": 31,
-      "read": true
+      "difficulty": 1,
+      "read": false
     },
     {
       "card_id": "Data Science & ML Fundamentals:10",
-      "difficulty": 62,
-      "read": true
+      "difficulty": 1,
+      "read": false
     },
     {
       "card_id": "Data Science & ML Fundamentals:11",
       "difficulty": 1,
-      "read": true
+      "read": false
     },
     {
       "card_id": "Data Science & ML Fundamentals:12",
@@ -258,12 +196,12 @@
     {
       "card_id": "Data Science & ML Fundamentals:13",
       "difficulty": 1,
-      "read": true
+      "read": false
     },
     {
       "card_id": "Data Science & ML Fundamentals:14",
       "difficulty": 1,
-      "read": true
+      "read": false
     },
     {
       "card_id": "Data Science & ML Fundamentals:15",
@@ -277,8 +215,8 @@
     },
     {
       "card_id": "Data Science & ML Fundamentals:17",
-      "difficulty": 98,
-      "read": true
+      "difficulty": 1,
+      "read": false
     },
     {
       "card_id": "Data Science & ML Fundamentals:18",
@@ -287,18 +225,18 @@
     },
     {
       "card_id": "Data Science & ML Fundamentals:19",
-      "difficulty": 53,
-      "read": true
+      "difficulty": 1,
+      "read": false
     },
     {
       "card_id": "Data Science & ML Fundamentals:2",
-      "difficulty": 36,
-      "read": true
+      "difficulty": 1,
+      "read": false
     },
     {
       "card_id": "Data Science & ML Fundamentals:20",
       "difficulty": 1,
-      "read": true
+      "read": false
     },
     {
       "card_id": "Data Science & ML Fundamentals:21",
@@ -307,8 +245,8 @@
     },
     {
       "card_id": "Data Science & ML Fundamentals:22",
-      "difficulty": 87,
-      "read": true
+      "difficulty": 1,
+      "read": false
     },
     {
       "card_id": "Data Science & ML Fundamentals:23",
@@ -317,8 +255,8 @@
     },
     {
       "card_id": "Data Science & ML Fundamentals:24",
-      "difficulty": 26,
-      "read": true
+      "difficulty": 1,
+      "read": false
     },
     {
       "card_id": "Data Science & ML Fundamentals:25",
@@ -327,8 +265,8 @@
     },
     {
       "card_id": "Data Science & ML Fundamentals:26",
-      "difficulty": 17,
-      "read": true
+      "difficulty": 1,
+      "read": false
     },
     {
       "card_id": "Data Science & ML Fundamentals:27",
@@ -338,7 +276,7 @@
     {
       "card_id": "Data Science & ML Fundamentals:28",
       "difficulty": 1,
-      "read": true
+      "read": false
     },
     {
       "card_id": "Data Science & ML Fundamentals:29",
@@ -347,8 +285,8 @@
     },
     {
       "card_id": "Data Science & ML Fundamentals:3",
-      "difficulty": 100,
-      "read": true
+      "difficulty": 1,
+      "read": false
     },
     {
       "card_id": "Data Science & ML Fundamentals:30",
@@ -357,33 +295,33 @@
     },
     {
       "card_id": "Data Science & ML Fundamentals:4",
-      "difficulty": 29,
-      "read": true
+      "difficulty": 1,
+      "read": false
     },
     {
       "card_id": "Data Science & ML Fundamentals:5",
-      "difficulty": 86,
-      "read": true
+      "difficulty": 1,
+      "read": false
     },
     {
       "card_id": "Data Science & ML Fundamentals:6",
-      "difficulty": 77,
-      "read": true
+      "difficulty": 1,
+      "read": false
     },
     {
       "card_id": "Data Science & ML Fundamentals:7",
-      "difficulty": 45,
-      "read": true
+      "difficulty": 1,
+      "read": false
     },
     {
       "card_id": "Data Science & ML Fundamentals:8",
-      "difficulty": 88,
-      "read": true
+      "difficulty": 1,
+      "read": false
     },
     {
       "card_id": "Data Science & ML Fundamentals:9",
-      "difficulty": 100,
-      "read": true
+      "difficulty": 1,
+      "read": false
     },
     {
       "card_id": "Database & SQL Fundamentals:1",
@@ -538,7 +476,7 @@
     {
       "card_id": "Database & SQL Fundamentals:9",
       "difficulty": 1,
-      "read": false
+      "read": true
     },
     {
       "card_id": "Github & Version Control Workflows:1",
@@ -558,7 +496,7 @@
     {
       "card_id": "Github & Version Control Workflows:12",
       "difficulty": 1,
-      "read": true
+      "read": false
     },
     {
       "card_id": "Github & Version Control Workflows:13",
@@ -648,7 +586,7 @@
     {
       "card_id": "Github & Version Control Workflows:4",
       "difficulty": 1,
-      "read": true
+      "read": false
     },
     {
       "card_id": "Github & Version Control Workflows:5",
@@ -682,8 +620,8 @@
     },
     {
       "card_id": "Linear Regression Fundamentals:10",
-      "difficulty": 1,
-      "read": false
+      "difficulty": 22,
+      "read": true
     },
     {
       "card_id": "Linear Regression Fundamentals:11",
```