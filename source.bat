@REM # Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
@REM # Licensed under the Apache License Version 2.0 (the "License"). You may not use this file except
@REM # in compliance with the License. A copy of the License is located at http://www.apache.org/licenses/
@REM # or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS,
@REM # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the
@REM # specific language governing permissions and limitations under the License.
@echo off
rem The sole purpose of this script is to make the command
rem
rem     source .venv/bin/activate
rem
rem (which activates a Python virtualenv on Linux or Mac OS X) work on Windows.
rem On Windows, this command just runs this batch file (the argument is ignored).
rem
rem Now we don't need to document a Windows command for activating a virtualenv.

echo Executing .venv\Scripts\activate.bat for you
.venv\Scripts\activate.bat
